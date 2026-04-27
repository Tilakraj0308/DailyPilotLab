from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    retry_scheduled = "retry_scheduled"
    done = "done"
    failed_terminal = "failed_terminal"


class JobType(str, Enum):
    chat_summary = "chat_summary"


class ChatSummaryJobPayload(BaseModel):
    user_id: str
    agent_id: str
    session_id: str
    window_index: int
    summary_row_id: str
    window_start_turn: int
    window_end_turn: int


def chat_summary_idempotency_key(
    user_id: str, agent_id: str, session_id: str, window_index: int
) -> str:
    return f"chat_summary:{user_id}:{agent_id}:{session_id}:{window_index}"


class WindowSummaryLLMResult(BaseModel):
    summary_text: str = Field(min_length=1)
    extracted_payload: dict[str, Any] = Field(default_factory=dict)
