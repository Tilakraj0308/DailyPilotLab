"""Google Calendar — Create tools."""

from __future__ import annotations

import logging
from typing import Any
import requests

logger = logging.getLogger(__name__)

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

TOOL_DEFINITIONS = [
    {
        "name": "create_google_calendar_event",
        "description": "Create a new event in the user's primary Google Calendar. IMPORTANT: Exact start and end date/times are critical. If the user does not provide enough information to determine the exact date and time, you MUST ask them for these details before creating the event.",
        "crud_type": "create",
        "parameters": {
            "summary": {
                "type": "string",
                "required": True,
                "description": "Title or summary of the event",
            },
            "start_time": {
                "type": "string",
                "required": True,
                "description": "Start time of the event in ISO 8601 format (e.g., 2026-06-18T09:00:00+05:30)",
            },
            "end_time": {
                "type": "string",
                "required": True,
                "description": "End time of the event in ISO 8601 format (e.g., 2026-06-18T10:00:00+05:30)",
            },
            "description": {
                "type": "string",
                "required": False,
                "description": "Optional description of the event",
            },
            "location": {
                "type": "string",
                "required": False,
                "description": "Optional location of the event",
            },
        },
    }
]


def create_event(
    connector: Any,
    user_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    description: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    """Create a new calendar event."""
    token = connector.ensure_access_token(user_id)
    
    payload: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }
    if description:
        payload["description"] = description
    if location:
        payload["location"] = location

    r = requests.post(
        f"{CALENDAR_API_BASE}/calendars/primary/events",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if r.status_code not in (200, 201):
        logger.warning("create calendar event failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    """Route a create tool call."""
    if tool_name == "create_google_calendar_event":
        return create_event(
            connector,
            user_id,
            summary=params["summary"],
            start_time=params["start_time"],
            end_time=params["end_time"],
            description=params.get("description"),
            location=params.get("location"),
        )

    raise ValueError(f"Unknown create tool: {tool_name}")
