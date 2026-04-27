from __future__ import annotations

import logging
from typing import Literal

from psycopg2.extras import Json

from db.dbConnection import get_dict_cursor
from models.agent_chat import AgentSummaryStatus

logger = logging.getLogger(__name__)


class AgentSessionAccessError(Exception):
    """Raised when session_id is not owned by the current user+agent pair."""

    pass


def ensure_default_agent(user_id: str) -> dict:
    """
    Idempotently ensure there is exactly one default agent per user.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.agents (user_id, kind, name)
            SELECT %s, 'default', 'Default Agent'
            WHERE NOT EXISTS (
                SELECT 1 FROM public.agents
                WHERE user_id = %s AND kind = 'default'
            )
            """,
            (user_id, user_id),
        )
        cur.execute(
            """
            SELECT id, user_id, kind, name, config, created_at, updated_at
            FROM public.agents
            WHERE user_id = %s AND kind = 'default'
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("Default agent row missing after ensure operation")
        return row


def _assert_session_owner(session_id: str, user_id: str, agent_id: str) -> None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT user_id, agent_id
            FROM public.agent_sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            raise AgentSessionAccessError(
                "Session id is not valid for this user+agent pair"
            )

        owner_user = str(row["user_id"])
        owner_agent = str(row["agent_id"])
        if owner_user != str(user_id) or owner_agent != str(agent_id):
            raise AgentSessionAccessError(
                "Session id is not valid for this user+agent pair"
            )


def _assert_agent_owner(agent_id: str, user_id: str) -> None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT user_id
            FROM public.agents
            WHERE id = %s
            """,
            (agent_id,),
        )
        row = cur.fetchone()
        if not row or str(row["user_id"]) != str(user_id):
            raise AgentSessionAccessError(
                "Agent id is not valid for this user"
            )


def get_or_create_agent_session(session_id: str, user_id: str, agent_id: str) -> str:
    _assert_agent_owner(agent_id=agent_id, user_id=user_id)
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.agent_sessions (id, user_id, agent_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (session_id, user_id, agent_id),
        )
    _assert_session_owner(session_id=session_id, user_id=user_id, agent_id=agent_id)
    return session_id


def save_agent_message(
    *,
    session_id: str,
    user_id: str,
    agent_id: str,
    role: str,
    content: str,
) -> dict:
    if role not in {"user", "assistant"}:
        raise ValueError("role must be one of: user, assistant")

    get_or_create_agent_session(session_id=session_id, user_id=user_id, agent_id=agent_id)

    with get_dict_cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (session_id,))
        cur.execute(
            """
            SELECT COALESCE(MAX(turn_index), -1) + 1 AS next_turn_index
            FROM public.agent_messages
            WHERE session_id = %s
            """,
            (session_id,),
        )
        row = cur.fetchone()
        next_turn_index = int(row["next_turn_index"])

        cur.execute(
            """
            INSERT INTO public.agent_messages (
                session_id, user_id, agent_id, role, content, turn_index
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, session_id, user_id, agent_id, role, content, turn_index, created_at
            """,
            (session_id, user_id, agent_id, role, content, next_turn_index),
        )
        inserted = cur.fetchone()
        cur.execute(
            """
            UPDATE public.agent_sessions
            SET updated_at = now()
            WHERE id = %s
            """,
            (session_id,),
        )
        return inserted


def load_agent_history(*, session_id: str, user_id: str, agent_id: str) -> list[dict]:
    _assert_session_owner(session_id=session_id, user_id=user_id, agent_id=agent_id)

    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT role, content, turn_index, created_at
            FROM public.agent_messages
            WHERE session_id = %s
            ORDER BY turn_index ASC, created_at ASC
            """,
            (session_id,),
        )
        return cur.fetchall()


def agent_session_exists(*, session_id: str, user_id: str, agent_id: str) -> bool:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM public.agent_sessions
            WHERE id = %s AND user_id = %s AND agent_id = %s
            """,
            (session_id, user_id, agent_id),
        )
        return cur.fetchone() is not None


def load_merged_session_history(
    *, session_id: str, user_id: str
) -> tuple[list[dict], Literal["agent", "legacy"]]:
    """
    Load chat history for the session. Prefer `agent_messages` (default agent) when the
    session exists in `agent_sessions`, else fall back to legacy `chat_messages`.
    """
    agent = ensure_default_agent(user_id)
    agent_id = str(agent["id"])
    if agent_session_exists(
        session_id=session_id, user_id=user_id, agent_id=agent_id
    ):
        rows = load_agent_history(
            session_id=session_id, user_id=user_id, agent_id=agent_id
        )
        out = [{"role": r["role"], "content": r["content"]} for r in rows]
        logger.info(
            "chat_history source=agent session_id=%s user_id=%s message_count=%s",
            session_id,
            user_id,
            len(out),
        )
        return out, "agent"

    from services.chat_db import load_history

    rows = load_history(session_id)
    out = [{"role": r["role"], "content": r["content"]} for r in rows]
    logger.info(
        "chat_history source=legacy session_id=%s user_id=%s message_count=%s",
        session_id,
        user_id,
        len(out),
    )
    return out, "legacy"


def list_merged_chat_sessions(user_id: str, limit: int, offset: int) -> list[dict]:
    """
    List sessions for the sidebar: default-agent `agent_sessions` union legacy-only
    `chat_sessions` (rows not duplicated when both exist for same id).
    """
    agent = ensure_default_agent(user_id)
    agent_id = str(agent["id"])
    with get_dict_cursor() as cur:
        cur.execute(
            """
            WITH agent_side AS (
                SELECT
                    s.id,
                    s.updated_at,
                    s.created_at,
                    (
                        SELECT m.content
                        FROM public.agent_messages m
                        WHERE m.session_id = s.id
                          AND m.role = 'user'
                        ORDER BY m.turn_index ASC NULLS LAST, m.created_at ASC
                        LIMIT 1
                    ) AS title
                FROM public.agent_sessions s
                WHERE s.user_id = %s AND s.agent_id = %s
            ),
            legacy AS (
                SELECT
                    s.id,
                    s.updated_at,
                    s.created_at,
                    (
                        SELECT m.content
                        FROM public.chat_messages m
                        WHERE m.session_id = s.id
                          AND m.role = 'user'
                        ORDER BY m.created_at ASC
                        LIMIT 1
                    ) AS title
                FROM public.chat_sessions s
                WHERE s.user_id = %s
                  AND NOT EXISTS (SELECT 1 FROM public.agent_sessions a WHERE a.id = s.id)
            )
            SELECT * FROM (
                SELECT * FROM agent_side
                UNION ALL
                SELECT * FROM legacy
            ) u
            ORDER BY u.updated_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, agent_id, user_id, limit, offset),
        )
        rows = cur.fetchall()
    logger.info(
        "chat_sessions merged list user_id=%s limit=%s offset=%s count=%s",
        user_id,
        limit,
        offset,
        len(rows),
    )
    return list(rows)


def load_agent_messages_in_turn_range(
    *,
    session_id: str,
    user_id: str,
    agent_id: str,
    start_turn: int,
    end_turn: int,
) -> list[dict]:
    _assert_session_owner(session_id=session_id, user_id=user_id, agent_id=agent_id)

    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT role, content, turn_index, created_at
            FROM public.agent_messages
            WHERE session_id = %s
              AND turn_index >= %s
              AND turn_index <= %s
            ORDER BY turn_index ASC, created_at ASC
            """,
            (session_id, start_turn, end_turn),
        )
        return cur.fetchall()


def ensure_summary_row(
    *,
    user_id: str,
    agent_id: str,
    session_id: str,
    window_index: int,
) -> dict:
    _assert_session_owner(session_id=session_id, user_id=user_id, agent_id=agent_id)

    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.chat_summaries (
                user_id, agent_id, session_id, window_index, status
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, agent_id, session_id, window_index)
            DO NOTHING
            RETURNING id, user_id, agent_id, session_id, window_index, status, retry_count, created_at, updated_at
            """,
            (
                user_id,
                agent_id,
                session_id,
                window_index,
                AgentSummaryStatus.pending.value,
            ),
        )
        row = cur.fetchone()
        if row:
            return row

        cur.execute(
            """
            SELECT id, user_id, agent_id, session_id, window_index, status, retry_count, created_at, updated_at
            FROM public.chat_summaries
            WHERE user_id = %s
              AND agent_id = %s
              AND session_id = %s
              AND window_index = %s
            LIMIT 1
            """,
            (user_id, agent_id, session_id, window_index),
        )
        existing = cur.fetchone()
        if not existing:
            raise RuntimeError("Failed to ensure chat summary row")
        return existing


def get_latest_summary_window_index(
    *,
    user_id: str,
    agent_id: str,
    session_id: str,
) -> int | None:
    _assert_session_owner(session_id=session_id, user_id=user_id, agent_id=agent_id)

    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT MAX(window_index) AS latest_window_index
            FROM public.chat_summaries
            WHERE user_id = %s
              AND agent_id = %s
              AND session_id = %s
            """,
            (user_id, agent_id, session_id),
        )
        row = cur.fetchone()
        if not row or row["latest_window_index"] is None:
            return None
        return int(row["latest_window_index"])


def get_existing_summary_window_indexes(
    *,
    user_id: str,
    agent_id: str,
    session_id: str,
) -> list[int]:
    _assert_session_owner(session_id=session_id, user_id=user_id, agent_id=agent_id)

    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT window_index
            FROM public.chat_summaries
            WHERE user_id = %s
              AND agent_id = %s
              AND session_id = %s
            ORDER BY window_index ASC
            """,
            (user_id, agent_id, session_id),
        )
        return [int(row["window_index"]) for row in cur.fetchall()]


def update_summary_status(
    *,
    summary_id: str,
    status: str,
    increment_retry: bool = False,
) -> dict | None:
    allowed_statuses = {s.value for s in AgentSummaryStatus}
    if status not in allowed_statuses:
        raise ValueError(f"status must be one of: {', '.join(sorted(allowed_statuses))}")

    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.chat_summaries
            SET
                status = %s,
                retry_count = retry_count + CASE WHEN %s THEN 1 ELSE 0 END,
                updated_at = now()
            WHERE id = %s
            RETURNING id, user_id, agent_id, session_id, window_index, status, retry_count, created_at, updated_at
            """,
            (status, increment_retry, summary_id),
        )
        return cur.fetchone()


def update_chat_summary_done(
    *,
    summary_id: str,
    summary_text: str,
    extracted_payload: dict,
) -> dict | None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.chat_summaries
            SET
                summary_text = %s,
                extracted_payload = %s,
                status = %s,
                error_message = NULL,
                updated_at = now()
            WHERE id = %s
            RETURNING id, user_id, agent_id, session_id, window_index, status, retry_count, created_at, updated_at
            """,
            (summary_text, Json(extracted_payload), AgentSummaryStatus.done.value, summary_id),
        )
        return cur.fetchone()


def update_chat_summary_failed(
    *,
    summary_id: str,
    error_message: str,
) -> dict | None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.chat_summaries
            SET
                status = %s,
                error_message = %s,
                updated_at = now()
            WHERE id = %s
            RETURNING id, user_id, agent_id, session_id, window_index, status, retry_count, created_at, updated_at
            """,
            (AgentSummaryStatus.failed_terminal.value, error_message, summary_id),
        )
        return cur.fetchone()
