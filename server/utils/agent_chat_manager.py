from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

from models.agent_chat import AgentChatStreamRequest, AgentSummaryStatus
from services.agent_chat_db import (
    ensure_summary_row,
    get_or_create_agent_session,
    load_agent_history,
    save_agent_message,
)
from services.chat_service import stream_chat
from utils.background_jobs.config import load_summary_worker_config
from utils.background_jobs.models import chat_summary_idempotency_key
from utils.background_jobs.repository import enqueue_chat_summary_job


def compute_closed_windows(
    total_messages: int,
    exchange_size: int = 2,
    window_exchanges: int = 10,
) -> list[int]:
    if total_messages < 0:
        raise ValueError("total_messages must be >= 0")
    if exchange_size <= 0:
        raise ValueError("exchange_size must be > 0")
    if window_exchanges <= 0:
        raise ValueError("window_exchanges must be > 0")

    messages_per_window = exchange_size * window_exchanges
    completed_windows = total_messages // messages_per_window
    return list(range(completed_windows))


def resolve_summary_cycle(default_cycle: int = 10) -> int:
    """
    Resolve summary cycle from env key `summary_cycle`.
    Falls back to default when missing/invalid/non-positive.
    """
    raw_value = os.getenv("summary_cycle")
    if raw_value is None:
        return default_cycle
    try:
        cycle = int(raw_value)
    except (TypeError, ValueError):
        return default_cycle
    if cycle <= 0:
        return default_cycle
    return cycle


async def stream_agent_chat(req: AgentChatStreamRequest, user_id: str) -> StreamingResponse:
    session_id = str(req.session_id)
    agent_id = str(req.agent_id)
    user_text = req.content
    logger.info(
        "agent_chat stream_start session_id=%s agent_id=%s user_id=%s content_len=%s",
        session_id,
        agent_id,
        user_id,
        len(user_text or ""),
    )

    await asyncio.to_thread(
        get_or_create_agent_session, session_id, user_id, agent_id
    )
    await asyncio.to_thread(
        save_agent_message,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
        role="user",
        content=user_text,
    )

    history_rows = await asyncio.to_thread(
        load_agent_history,
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
    )
    history = [{"role": row["role"], "content": row["content"]} for row in history_rows]

    async def event_stream():
        full_response = ""
        async for token in stream_chat(history, user_id):
            full_response += token
            yield f'data: {json.dumps({"type": "token", "content": token})}\n\n'

        await asyncio.to_thread(
            save_agent_message,
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            role="assistant",
            content=full_response,
        )
        await asyncio.to_thread(
            process_post_assistant_message,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
        )
        yield f'data: {json.dumps({"type": "done", "content": ""})}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def process_post_assistant_message(*, user_id: str, agent_id: str, session_id: str) -> None:
    messages = load_agent_history(
        session_id=session_id,
        user_id=user_id,
        agent_id=agent_id,
    )
    cycle = resolve_summary_cycle()
    closed_windows = compute_closed_windows(
        total_messages=len(messages),
        window_exchanges=cycle,
    )
    logger.info(
        "post_assistant session_id=%s message_count=%s summary_cycle=%s closed_windows=%s",
        session_id,
        len(messages),
        cycle,
        closed_windows,
    )
    if not closed_windows:
        logger.info(
            "post_assistant: no closed windows yet (need more exchanges for cycle=%s)",
            cycle,
        )
        return

    messages_per_window = 2 * cycle
    worker_cfg = load_summary_worker_config()
    logger.info(
        "post_assistant: worker enabled in config=%s (set SUMMARY_WORKER_ENABLED=true to process jobs)",
        worker_cfg.enabled,
    )

    for window_index in closed_windows:
        row = ensure_summary_row(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            window_index=window_index,
        )
        st = str(row["status"])
        if st in (
            AgentSummaryStatus.done.value,
            AgentSummaryStatus.failed_terminal.value,
        ):
            continue

        start_turn = window_index * messages_per_window
        end_turn = start_turn + messages_per_window - 1
        payload = {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "window_index": window_index,
            "summary_row_id": str(row["id"]),
            "window_start_turn": start_turn,
            "window_end_turn": end_turn,
        }
        idem = chat_summary_idempotency_key(user_id, agent_id, session_id, window_index)
        job_id = enqueue_chat_summary_job(
            payload=payload,
            idempotency_key=idem,
            max_attempts=worker_cfg.max_job_retries,
        )
        if job_id:
            logger.info(
                "summary job enqueued job_id=%s idempotency_key=%s window_index=%s",
                job_id,
                idem,
                window_index,
            )
        else:
            logger.info(
                "summary job enqueue skipped (duplicate idempotency) idempotency_key=%s window_index=%s",
                idem,
                window_index,
            )
