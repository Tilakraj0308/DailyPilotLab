"""Shared Gmail route helpers (permissions, errors, history logging)."""

from __future__ import annotations

import logging

import requests.exceptions
from fastapi import HTTPException

from connectors import db
from connectors import history

logger = logging.getLogger(__name__)

_GMAIL_RECONNECT_DETAIL = (
    "Gmail access was denied or expired; reconnect your Gmail connector."
)

_GMAIL_AI_REPLY_SYSTEM = (
    "You draft email replies only. Output must follow the required JSON schema. "
    "Write a polite, concise reply body the user can paste into Gmail. "
    "Do not include instructions about sending, clicking send, or using the UI. "
    "Do not claim the message was sent. "
    "Optional subject: only if a clearer subject helps; otherwise omit or null."
)


def require_gmail_tool_permission(user_id: str, crud_type: str, *, feature: str) -> None:
    """Raise 403 when connector_tool_permissions disables this CRUD type for Gmail."""
    permissions = db.get_tool_permissions(user_id, "gmail")
    if not permissions.get(crud_type, True):
        raise HTTPException(
            status_code=403,
            detail=f"{feature} is disabled: enable '{crud_type}' for the Gmail connector.",
        )


def map_gmail_upstream_exc(exc: Exception) -> HTTPException:
    """Map Gmail HTTP client failures to API responses (404 when resource missing)."""
    if isinstance(exc, requests.exceptions.HTTPError):
        resp = exc.response
        if resp is not None:
            if resp.status_code == 404:
                return HTTPException(status_code=404, detail="Gmail resource not found")
            if resp.status_code in (401, 403):
                return HTTPException(status_code=401, detail=_GMAIL_RECONNECT_DETAIL)
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


def log_gmail_ui_tool(
    user_id: str,
    *,
    tool_name: str,
    crud_type: str,
    params: dict[str, object | None],
    result_summary: dict[str, object],
) -> None:
    clean_params = {k: v for k, v in params.items() if v is not None}
    clean_summary = {k: v for k, v in result_summary.items() if v is not None}
    try:
        history.log_tool_call(
            user_id=user_id,
            provider_key="gmail",
            tool_name=tool_name,
            crud_type=crud_type,
            params=clean_params or None,
            result_summary=clean_summary or None,
            status="success",
            error_message=None,
            triggered_by="user",
            ai_tool_response=None,
        )
    except Exception as e:
        logger.warning("Failed to log gmail UI tool history: %s", e)


__all__ = [
    "_GMAIL_AI_REPLY_SYSTEM",
    "log_gmail_ui_tool",
    "map_gmail_upstream_exc",
    "require_gmail_tool_permission",
]
