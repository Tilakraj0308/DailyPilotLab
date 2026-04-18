"""Gmail — Update tools (send draft)."""

from __future__ import annotations

from typing import Any

from connectors.providers.gmail import gmail_api

TOOL_DEFINITIONS = [
    {
        "name": "gmail_send_draft",
        "description": "Send an existing Gmail draft by draft id",
        "crud_type": "update",
        "parameters": {
            "draft_id": {
                "type": "str",
                "required": True,
                "description": "Draft resource id to send",
            },
        },
    },
]


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    if tool_name != "gmail_send_draft":
        raise ValueError(f"Unknown update tool: {tool_name}")

    token = connector.ensure_access_token(user_id)
    draft_id = params["draft_id"]
    sent = gmail_api.send_draft(access_token=token, draft_id=draft_id)
    if not isinstance(sent, dict):
        raise ValueError("Invalid send response from Gmail")
    sent_id = str(sent.get("id") or "")
    return {"ok": True, "id": sent_id}
