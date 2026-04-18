from __future__ import annotations

from datetime import datetime

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


class GmailThreadSummaryOut(BaseModel):
    id: str
    snippet: str | None = None
    subject: str | None = None
    from_addr: str | None = None
    internal_date_ms: str | None = None
    label_ids: list[str] = Field(default_factory=list)


class GmailPriorityResponse(BaseModel):
    query: str
    items: list[GmailThreadSummaryOut]


class GmailDraftCreateRequest(BaseModel):
    thread_id: str | None = None
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str
    body_text: str


class GmailDraftCreateResponse(BaseModel):
    draft_id: str
    message_id: str | None = None
    thread_id: str | None = None


class GmailDraftSendRequest(BaseModel):
    # Intentionally empty: sending is explicit by route + draft id path param
    pass
