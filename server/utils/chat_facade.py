"""
Application facade for merged chat session APIs.

Routes should depend on this module instead of importing `services.agent_chat_db` directly.
"""

from __future__ import annotations

from typing import Any

from services.agent_chat_db import (
    ensure_default_agent,
    list_merged_chat_sessions,
    load_merged_session_history,
)


def list_chat_sessions_for_user(user_id: str, *, limit: int, offset: int) -> list[dict[str, Any]]:
    return list_merged_chat_sessions(user_id, limit=limit, offset=offset)


def load_merged_history(session_id: str, user_id: str) -> tuple[list[Any], Any]:
    return load_merged_session_history(session_id=session_id, user_id=user_id)


def ensure_user_default_agent(user_id: str) -> dict[str, Any]:
    return ensure_default_agent(user_id)
