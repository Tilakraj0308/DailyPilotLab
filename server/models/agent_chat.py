from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AgentKind(str, Enum):
    default = "default"
    custom = "custom"


class AgentSummaryStatus(str, Enum):
    pending = "pending"
    done = "done"
    pending_retry = "pending_retry"
    failed_terminal = "failed_terminal"


class AgentChatStreamRequest(BaseModel):
    agent_id: UUID
    session_id: UUID
    content: str = Field(min_length=1)


class AgentRecord(BaseModel):
    id: str
    user_id: str
    kind: AgentKind
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
