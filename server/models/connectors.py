from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConnectorStartRequest(BaseModel):
    """Client redirect after OAuth completes (browser or deep link)."""

    return_to: str | None = Field(
        default=None,
        description="URL to redirect user after OAuth (e.g. dailypilot:// or http://localhost:8081/connectors/callback)",
    )


class ConnectorStartResponse(BaseModel):
    authorization_url: str
    state: str


class ConnectorStatusItem(BaseModel):
    provider_key: str
    display_name: str
    status: str
    scopes: list[str] = Field(default_factory=list)
    connected_at: datetime | None = None
    provider_email: str | None = None
    error_message: str | None = None
    selected_resource_id: str | None = None
    selected_resource_name: str | None = None


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatusItem]


class ConnectorDisconnectResponse(BaseModel):
    ok: bool
    provider_key: str


class SelectTaskListRequest(BaseModel):
    task_list_id: str
    task_list_title: str | None = None


class TaskListItemOut(BaseModel):
    id: str
    title: str


class TaskListsResponse(BaseModel):
    items: list[TaskListItemOut]


class CreateGoogleTaskRequest(BaseModel):
    title: str
    notes: str | None = None


class UpdateGoogleTaskRequest(BaseModel):
    title: str | None = None
    notes: str | None = None
    status: str | None = None
    completed: bool | None = None
