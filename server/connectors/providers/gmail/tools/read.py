"""Gmail — Read tools."""

from __future__ import annotations

from typing import Any

from connectors.providers.gmail import gmail_api
from connectors.providers.gmail.thread_helpers import (
    GMAIL_DEFAULT_PRIORITY_Q,
    fetch_priority_threads,
    normalize_thread_detail_dict,
)

TOOL_DEFINITIONS = [
    {
        "name": "gmail_list_priority_threads",
        "description": (
            "List priority Gmail threads: inbox messages for a query, deduped by thread, "
            "then hydrated with metadata (same flow as the priority inbox view)."
        ),
        "crud_type": "read",
        "parameters": {
            "max_results": {
                "type": "int",
                "required": False,
                "default": 30,
                "description": "Max messages to list before thread dedupe (default 30, clamped 1–50 by API helper)",
            },
            "q": {
                "type": "str",
                "required": False,
                "default": GMAIL_DEFAULT_PRIORITY_Q,
                "description": "Gmail search query (default last-14-days inbox)",
            },
        },
    },
    {
        "name": "gmail_get_thread",
        "description": "Fetch a Gmail thread by id with optional message format (metadata by default)",
        "crud_type": "read",
        "parameters": {
            "thread_id": {
                "type": "str",
                "required": True,
                "description": "Gmail thread id",
            },
            "message_format": {
                "type": "str",
                "required": False,
                "default": "metadata",
                "description": "Gmail API format parameter (e.g. metadata, full)",
            },
        },
    },
]


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    token = connector.ensure_access_token(user_id)

    if tool_name == "gmail_list_priority_threads":
        max_results = params.get("max_results", 30)
        q = params.get("q", GMAIL_DEFAULT_PRIORITY_Q)
        return fetch_priority_threads(access_token=token, max_results=max_results, q=q)

    if tool_name == "gmail_get_thread":
        thread_id = params["thread_id"]
        message_format = params.get("message_format", "metadata")
        raw = gmail_api.get_thread(
            access_token=token,
            thread_id=thread_id,
            message_format=message_format,
        )
        if not isinstance(raw, dict):
            raise ValueError("Invalid thread response from Gmail")
        return normalize_thread_detail_dict(raw)

    raise ValueError(f"Unknown read tool: {tool_name}")
