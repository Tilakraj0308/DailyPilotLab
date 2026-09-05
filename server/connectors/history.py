"""
Tool execution history logging.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from db.dbConnection import get_dict_cursor

logger = logging.getLogger(__name__)


def log_tool_call(
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
    """Log a single tool execution to the database."""
    params_json = json.dumps(params) if params else None
    result_json = json.dumps(result_summary) if result_summary else None

    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.connector_tool_history
                (user_id, provider_key, tool_name, crud_type, params, result_summary, status, error_message, triggered_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                provider_key,
                tool_name,
                crud_type,
                params_json,
                result_json,
                status,
                error_message,
                triggered_by,
            ),
        )


def get_recent_history(
    user_id: str,
    provider_key: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return recent tool execution history for a user, optionally filtered by provider."""
    query = """
        SELECT
            id,
            provider_key,
            tool_name,
            crud_type,
            params,
            result_summary,
            status,
            error_message,
            triggered_by,
            created_at
        FROM public.connector_tool_history
        WHERE user_id = %s
    """
    args: list[Any] = [user_id]

    if provider_key:
        query += " AND provider_key = %s"
        args.append(provider_key)

    query += " ORDER BY created_at DESC LIMIT %s"
    args.append(limit)

    with get_dict_cursor() as cur:
        cur.execute(query, tuple(args))
        rows = cur.fetchall()
        
    return [dict(row) for row in rows]
