"""Google Calendar — Read tools."""

from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timezone, timedelta

import requests

logger = logging.getLogger(__name__)

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

TOOL_DEFINITIONS = [
    {
        "name": "list_google_calendar_events",
        "description": "List upcoming events from the user's primary Google Calendar",
        "crud_type": "read",
        "parameters": {
            "max_results": {
                "type": "int",
                "required": False,
                "default": 10,
                "description": "Maximum number of events to return (default 10)",
            },
            "days_ahead": {
                "type": "int",
                "required": False,
                "default": 7,
                "description": "Number of days ahead to look for events (default 7)",
            },
        },
    }
]


def list_events(
    connector: Any,
    user_id: str,
    max_results: int = 10,
    days_ahead: int = 7,
) -> list[dict[str, Any]]:
    """List upcoming calendar events."""
    token = connector.ensure_access_token(user_id)
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    r = requests.get(
        f"{CALENDAR_API_BASE}/calendars/primary/events",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
        },
        timeout=30,
    )
    if r.status_code != 200:
        logger.warning("list calendar events failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    data = r.json()
    return data.get("items") or []


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    """Route a read tool call."""
    if tool_name == "list_google_calendar_events":
        return list_events(
            connector,
            user_id,
            max_results=params.get("max_results", 10),
            days_ahead=params.get("days_ahead", 7),
        )

    raise ValueError(f"Unknown read tool: {tool_name}")
