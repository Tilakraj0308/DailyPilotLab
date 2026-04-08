"""
Pydantic schemas for the Connectors module.

Used by connector route handlers for request validation
and response serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class ConnectorStatus(BaseModel):
    """Status of a single connector for a user."""
    provider: str                                    # 'google_calendar'
    connected: bool
    provider_account_email: Optional[str] = None     # 'user@gmail.com'
    scopes: list[str] = []
    expires_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    needs_reconnect: bool = False                    # True if revoked_at is set

    model_config = ConfigDict(from_attributes=True)


class ConnectorListResponse(BaseModel):
    """List of all connectors for a user."""
    connectors: list[ConnectorStatus]


class CalendarEvent(BaseModel):
    """A single calendar event."""
    id: str
    summary: str
    start: str                                       # ISO datetime string
    end: str                                         # ISO datetime string
    location: Optional[str] = None
    status: str = "confirmed"                        # confirmed, tentative, cancelled
    is_all_day: bool = False


class CalendarEventsResponse(BaseModel):
    """Response for the events endpoint."""
    events: list[CalendarEvent]
    synced_at: str                                   # ISO datetime of this fetch
