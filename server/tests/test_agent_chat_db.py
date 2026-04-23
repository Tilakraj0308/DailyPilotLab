from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from psycopg2 import extras, sql

from db.dbConnection import get_connection
from services.agent_chat_db import (
    AgentSessionAccessError,
    ensure_default_agent,
    get_or_create_agent_session,
    load_agent_history,
    save_agent_message,
)
from models.agent_chat import AgentChatStreamRequest, AgentSummaryStatus


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "20260423_agent_chat_core.sql"
)


def _load_agent_chat_migration_sql() -> str:
    assert MIGRATION_PATH.exists(), f"Missing migration file: {MIGRATION_PATH}"
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_agent_chat_tables_exist():
    migration_sql = _load_agent_chat_migration_sql()

    assert "create table if not exists public.agents" in migration_sql
    assert "create table if not exists public.agent_sessions" in migration_sql
    assert "create table if not exists public.agent_messages" in migration_sql
    assert "create table if not exists public.chat_summaries" in migration_sql
    assert "create unique index if not exists idx_agents_one_default_per_user" in migration_sql


def test_agent_chat_constraints_exist():
    migration_sql = _load_agent_chat_migration_sql()

    assert "check (role in ('user', 'assistant'))" in migration_sql
    assert (
        "check (status in ('pending', 'done', 'pending_retry', 'failed_terminal'))"
        in migration_sql
    )
    assert "unique (id, user_id, agent_id)" in migration_sql
    assert "unique (session_id, turn_index)" in migration_sql
    assert "unique (user_id, agent_id, session_id, window_index)" in migration_sql
    assert "foreign key (session_id, user_id, agent_id)" in migration_sql
    assert "references public.agent_sessions(id, user_id, agent_id)" in migration_sql
    assert "foreign key (agent_id, user_id)" in migration_sql
    assert "references public.agents(id, user_id)" in migration_sql


def test_agent_chat_performance_indexes_exist():
    migration_sql = _load_agent_chat_migration_sql()

    assert "create index if not exists idx_agent_sessions_user_agent_updated_at" in migration_sql
    assert "create index if not exists idx_agent_messages_session_created_at" in migration_sql
    assert "create index if not exists idx_agent_messages_user_agent_session_turn" in migration_sql
    assert "create index if not exists idx_chat_summaries_session_window" in migration_sql
    assert "create index if not exists idx_chat_summaries_status_updated_at" in migration_sql


def test_agent_chat_migration_executes_in_isolated_schema():
    test_schema = "test_agent_chat_schema"
    rewritten_sql = _load_agent_chat_migration_sql().replace("public.", f"{test_schema}.")

    with get_connection() as conn:
        conn.autocommit = True
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            try:
                cur.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(test_schema)
                    )
                )
                cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(test_schema)))
                cur.execute(
                    sql.SQL("CREATE TABLE {}.users (auth_id TEXT PRIMARY KEY)").format(
                        sql.Identifier(test_schema)
                    )
                )
                cur.execute(rewritten_sql)

                cur.execute(
                    """
                    SELECT
                        to_regclass(%s)::text AS agents_tbl,
                        to_regclass(%s)::text AS sessions_tbl,
                        to_regclass(%s)::text AS messages_tbl,
                        to_regclass(%s)::text AS summaries_tbl
                    """,
                    (
                        f"{test_schema}.agents",
                        f"{test_schema}.agent_sessions",
                        f"{test_schema}.agent_messages",
                        f"{test_schema}.chat_summaries",
                    ),
                )
                row = cur.fetchone()
                assert row["agents_tbl"] == f"{test_schema}.agents"
                assert row["sessions_tbl"] == f"{test_schema}.agent_sessions"
                assert row["messages_tbl"] == f"{test_schema}.agent_messages"
                assert row["summaries_tbl"] == f"{test_schema}.chat_summaries"

                cur.execute(
                    """
                    SELECT c.conname
                    FROM pg_constraint c
                    JOIN pg_class t ON t.oid = c.conrelid
                    JOIN pg_namespace n ON n.oid = t.relnamespace
                    JOIN pg_class rt ON rt.oid = c.confrelid
                    JOIN pg_namespace rn ON rn.oid = rt.relnamespace
                    WHERE c.contype = 'f'
                      AND n.nspname = %s
                      AND t.relname IN ('agent_messages', 'chat_summaries')
                      AND rn.nspname = %s
                      AND rt.relname = 'agent_sessions'
                      AND array_length(c.conkey, 1) = 3
                    LIMIT 1
                    """,
                    (test_schema, test_schema),
                )
                assert cur.fetchone() is not None
            finally:
                cur.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(test_schema)
                    )
                )


def _ensure_test_user_exists(user_id: str) -> None:
    with get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.users (auth_id, email)
                VALUES (%s, %s)
                ON CONFLICT (auth_id) DO NOTHING
                """,
                (user_id, f"{user_id}@agent-chat.test"),
            )


def _ensure_agent_chat_schema_applied() -> None:
    with get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(MIGRATION_PATH.read_text(encoding="utf-8"))


def test_ensure_default_agent_idempotent():
    user_id = "task2-agent-default-idempotent-user"
    _ensure_agent_chat_schema_applied()
    _ensure_test_user_exists(user_id)

    first = ensure_default_agent(user_id)
    second = ensure_default_agent(user_id)

    assert first["id"] == second["id"]
    assert first["user_id"] == user_id
    assert first["kind"] == "default"
    assert second["kind"] == "default"


def _insert_agent(*, user_id: str, agent_id: str, kind: str, name: str) -> None:
    with get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.agents (id, user_id, kind, name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (agent_id, user_id, kind, name),
            )


def test_session_rejects_cross_agent_access():
    user_id = "task3-cross-agent-access-user"
    session_id = "00000000-0000-0000-0000-000000000201"
    agent_id_one = "00000000-0000-0000-0000-000000000301"
    agent_id_two = "00000000-0000-0000-0000-000000000302"

    _ensure_agent_chat_schema_applied()
    _ensure_test_user_exists(user_id)
    _insert_agent(user_id=user_id, agent_id=agent_id_one, kind="default", name="A1")
    _insert_agent(user_id=user_id, agent_id=agent_id_two, kind="custom", name="A2")

    get_or_create_agent_session(session_id, user_id, agent_id_one)

    with pytest.raises(AgentSessionAccessError):
        get_or_create_agent_session(session_id, user_id, agent_id_two)


def test_save_and_load_agent_messages_preserve_turn_order():
    unique_suffix = uuid4().hex
    user_id = f"task3-message-persistence-user-{unique_suffix}"
    session_id = str(uuid4())
    agent_id = str(uuid4())

    _ensure_agent_chat_schema_applied()
    _ensure_test_user_exists(user_id)
    _insert_agent(user_id=user_id, agent_id=agent_id, kind="default", name="A1")
    get_or_create_agent_session(session_id, user_id, agent_id)

    first = save_agent_message(
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        role="user",
        content="hello from user",
    )
    second = save_agent_message(
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        role="assistant",
        content="hello from assistant",
    )
    history = load_agent_history(
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
    )

    assert first["turn_index"] == 0
    assert second["turn_index"] == 1
    assert [row["role"] for row in history] == ["user", "assistant"]
    assert [row["content"] for row in history] == [
        "hello from user",
        "hello from assistant",
    ]


def test_save_agent_message_rejects_invalid_role():
    unique_suffix = uuid4().hex
    user_id = f"task3-invalid-role-user-{unique_suffix}"
    session_id = str(uuid4())
    agent_id = str(uuid4())

    _ensure_agent_chat_schema_applied()
    _ensure_test_user_exists(user_id)
    _insert_agent(user_id=user_id, agent_id=agent_id, kind="default", name="A1")
    get_or_create_agent_session(session_id, user_id, agent_id)

    with pytest.raises(ValueError, match="role must be one of: user, assistant"):
        save_agent_message(
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            role="system",
            content="not allowed",
        )


def test_load_agent_history_rejects_cross_agent_access():
    user_id = "task3-history-ownership-user"
    session_id = "00000000-0000-0000-0000-000000000221"
    agent_id_one = "00000000-0000-0000-0000-000000000321"
    agent_id_two = "00000000-0000-0000-0000-000000000322"

    _ensure_agent_chat_schema_applied()
    _ensure_test_user_exists(user_id)
    _insert_agent(user_id=user_id, agent_id=agent_id_one, kind="default", name="A1")
    _insert_agent(user_id=user_id, agent_id=agent_id_two, kind="custom", name="A2")
    get_or_create_agent_session(session_id, user_id, agent_id_one)

    with pytest.raises(AgentSessionAccessError):
        load_agent_history(
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id_two,
        )


def test_session_rejects_cross_user_agent_id_misuse():
    user_id = "task3-cross-user-agent-misuse-user"
    foreign_user_id = "task3-cross-user-agent-owner"
    session_id = "00000000-0000-0000-0000-000000000271"
    foreign_agent_id = "00000000-0000-0000-0000-000000000371"

    _ensure_agent_chat_schema_applied()
    _ensure_test_user_exists(user_id)
    _ensure_test_user_exists(foreign_user_id)
    _insert_agent(
        user_id=foreign_user_id,
        agent_id=foreign_agent_id,
        kind="custom",
        name="Foreign Agent",
    )

    with pytest.raises(AgentSessionAccessError):
        get_or_create_agent_session(session_id, user_id, foreign_agent_id)


def test_agent_chat_models_minimal_contract():
    request = AgentChatStreamRequest(
        agent_id="00000000-0000-0000-0000-000000000301",
        session_id="00000000-0000-0000-0000-000000000201",
        content="hello",
    )
    assert str(request.agent_id).endswith("301")
    assert request.content == "hello"
    assert AgentSummaryStatus.pending_retry.value == "pending_retry"

    with pytest.raises(ValidationError):
        AgentChatStreamRequest(
            agent_id="not-a-uuid",
            session_id="00000000-0000-0000-0000-000000000201",
            content="hello",
        )

    with pytest.raises(ValidationError):
        AgentChatStreamRequest(
            agent_id="00000000-0000-0000-0000-000000000301",
            session_id="also-not-a-uuid",
            content="hello",
        )

    with pytest.raises(ValidationError):
        AgentChatStreamRequest(
            agent_id="00000000-0000-0000-0000-000000000301",
            session_id="00000000-0000-0000-0000-000000000201",
            content="",
        )
