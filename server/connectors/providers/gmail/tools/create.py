"""Gmail — Create tools (drafts)."""

from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any

from connectors.providers.gmail import gmail_api


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


TOOL_DEFINITIONS = [
    {
        "name": "gmail_create_draft",
        "description": "Create a Gmail draft (optionally as a reply when thread_id is set)",
        "crud_type": "create",
        "parameters": {
            "subject": {
                "type": "str",
                "required": True,
                "description": "Email subject",
            },
            "body_text": {
                "type": "str",
                "required": True,
                "description": "Plain-text body",
            },
            "to": {
                "type": "list",
                "required": False,
                "description": "To addresses",
            },
            "cc": {
                "type": "list",
                "required": False,
                "description": "Cc addresses",
            },
            "bcc": {
                "type": "list",
                "required": False,
                "description": "Bcc addresses",
            },
            "thread_id": {
                "type": "str",
                "required": False,
                "description": "Optional thread id for a reply draft",
            },
        },
    },
]


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    if tool_name != "gmail_create_draft":
        raise ValueError(f"Unknown create tool: {tool_name}")

    token = connector.ensure_access_token(user_id)
    subject = params["subject"]
    body_text = params["body_text"]
    to_addrs = _as_str_list(params.get("to"))
    cc_addrs = _as_str_list(params.get("cc"))
    bcc_addrs = _as_str_list(params.get("bcc"))
    thread_id = params.get("thread_id")

    msg = EmailMessage()
    msg["Subject"] = subject
    if to_addrs:
        msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)
    if bcc_addrs:
        msg["Bcc"] = ", ".join(bcc_addrs)
    msg.set_content(body_text)
    raw_bytes = msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")

    api_body: dict = {"message": {"raw": raw_b64}}
    if thread_id:
        api_body["message"]["threadId"] = thread_id

    created = gmail_api.create_draft(access_token=token, body=api_body)
    if not isinstance(created, dict):
        raise ValueError("Invalid draft response from Gmail")
    draft_id = str(created.get("id") or "")
    inner = created.get("message")
    message_id = None
    out_thread_id = None
    if isinstance(inner, dict):
        mid = inner.get("id")
        if mid is not None:
            message_id = str(mid)
        tid = inner.get("threadId")
        if tid is not None:
            out_thread_id = str(tid)
    return {
        "draft_id": draft_id,
        "message_id": message_id,
        "thread_id": out_thread_id,
    }
