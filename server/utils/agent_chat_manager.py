from __future__ import annotations

import asyncio
import json
import os

from fastapi.responses import StreamingResponse

from models.agent_chat import AgentChatStreamRequest, AgentSummaryStatus
from services.agent_chat_db import (
    get_or_create_agent_session,
    save_agent_message,
    load_agent_history,
    ensure_summary_row,
    get_existing_summary_window_indexes,
    update_summary_status,
)
from services.chat_service import stream_chat


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


def mark_summary_retryable(summary_id: str) -> dict | None:
    return update_summary_status(
        summary_id=summary_id,
        status=AgentSummaryStatus.pending_retry.value,
        increment_retry=True,
    )


async def stream_agent_chat(req: AgentChatStreamRequest, user_id: str) -> StreamingResponse:
    session_id = str(req.session_id)
    agent_id = str(req.agent_id)
    user_text = req.content

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
    closed_windows = compute_closed_windows(
        total_messages=len(messages),
        window_exchanges=resolve_summary_cycle(),
    )
    if not closed_windows:
        return

    existing_windows = get_existing_summary_window_indexes(
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
    )
    missing_windows = sorted(set(closed_windows) - set(existing_windows))

    for window_index in missing_windows:
        ensure_summary_row(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            window_index=window_index,
        )
