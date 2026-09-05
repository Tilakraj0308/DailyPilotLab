"""
Tool Executor — routes tool calls to the correct provider and logs history.

Handles authentication, permission checks, execution, and audit logging.
"""

from __future__ import annotations

import importlib
import logging
import traceback
from typing import Any

from connectors import db
from connectors.base_connector import ConnectorReAuthError
from connectors.providers import PROVIDER_MAP
from connectors.tool_registry import resolve_tool

logger = logging.getLogger(__name__)


class ToolPermissionDenied(Exception):
    """Raised when a user has disabled a CRUD type for a provider."""
    pass


class ToolNotFound(Exception):
    """Raised when the requested tool name doesn't exist."""
    pass


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


def _get_tool_module(provider_key: str, crud_type: str) -> Any:
    """Import the correct CRUD module for a provider."""
    return importlib.import_module(
        f"connectors.providers.{provider_key}.tools.{crud_type}"
    )


def execute_tool(
    user_id: str,
    tool_name: str,
    params: dict,
    triggered_by: str = "user",
) -> dict[str, Any]:
    """
    Execute a tool call.

    1. Resolve tool_name → provider + definition
    2. Check user has the provider connected
    3. Check CRUD permission is enabled
    4. Instantiate connector, call the tool's execute()
    5. Log to history
    6. Return result
    """
    # 1. Resolve
    resolved = resolve_tool(tool_name)
    if not resolved:
        raise ToolNotFound(f"Tool '{tool_name}' not found in any provider.")
    provider_key, tool_def = resolved
    crud_type = tool_def.get("crud_type", "read")

    # 2. Check connected
    connected = db.list_connected_providers(user_id)
    if provider_key not in connected:
        raise ToolPermissionDenied(
            f"Provider '{provider_key}' is not connected. Please connect it first."
        )

    # 3. Check permission
    permissions = db.get_tool_permissions(user_id, provider_key)
    if not permissions.get(crud_type, True):
        raise ToolPermissionDenied(
            f"You have disabled '{crud_type}' access for {provider_key}. "
            f"Enable it in your connector settings to use this tool."
        )

    # 4. Execute
    connector = PROVIDER_MAP[provider_key]()
    try:
        tool_module = _get_tool_module(provider_key, crud_type)
        result = tool_module.execute(connector, user_id, tool_name, params)
    except ConnectorReAuthError as e:
        auth_url = None
        try:
            auth_url, _ = connector.build_start_authorization_url(user_id, return_to=None)
        except Exception as auth_err:
            logger.warning("Failed to build start authorization url for %s: %s", provider_key, auth_err)

        reauth_response = {
            "ok": False,
            "error_type": "requires_reauth",
            "provider": provider_key,
            "auth_url": auth_url,
            "error": (
                f"Re-authentication required for {provider_key}. "
                f"Please instruct the user to reconnect using this authorization URL: {auth_url}"
                if auth_url
                else f"Re-authentication required for {provider_key}."
            ),
        }
        _log_history(
            user_id,
            provider_key,
            tool_name,
            crud_type,
            params,
            None,
            "error",
            str(e),
            triggered_by,
        )
        logger.warning("Tool execution requires re-authentication: %s — %s", tool_name, e)
        return reauth_response
    except Exception as e:
        # Log failure (same shape as chat_service tool message on error)
        _log_history(
            user_id,
            provider_key,
            tool_name,
            crud_type,
            params,
            None,
            "error",
            str(e),
            triggered_by,
        )
        logger.error("Tool execution failed: %s — %s", tool_name, traceback.format_exc())
        raise ToolExecutionError(f"Tool '{tool_name}' failed: {e}") from e

    # 5. Log success
    result_summary = _summarize_result(result)
    ai_tool_response = {"ok": True, "tool": tool_name, "result": result}
    _log_history(
        user_id,
        provider_key,
        tool_name,
        crud_type,
        params,
        result_summary,
        "success",
        None,
        triggered_by,
    )

    # 6. Return
    return ai_tool_response


def _summarize_result(result: Any) -> dict | None:
    """Create a compact summary of the result for the history table."""
    if result is None:
        return None
    if isinstance(result, dict):
        return {k: v for k, v in result.items() if k in ("id", "title", "status", "ok")}
    if isinstance(result, list):
        return {"count": len(result)}
    return {"value": str(result)[:200]}


def _log_history(
    user_id: str,
    provider_key: str,
    tool_name: str,
    crud_type: str,
    params: dict | None,
    result_summary: dict | None,
    status: str,
    error_message: str | None,
    triggered_by: str,
) -> None:
    """Log a tool call to history. Fails silently to not block execution."""
    try:
        from connectors import history
        history.log_tool_call(
            user_id=user_id,
            provider_key=provider_key,
            tool_name=tool_name,
            crud_type=crud_type,
            params=params,
            result_summary=result_summary,
            status=status,
            error_message=error_message,
            triggered_by=triggered_by,
        )
    except Exception as e:
        logger.warning("Failed to log tool history: %s", e)
