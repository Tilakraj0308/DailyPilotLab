"""Notion — Delete tools (archive page)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from connectors.providers.notion.notion_api import NOTION_API_BASE, notion_headers

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "archive_notion_page",
        "description": "Archive (soft-delete) a Notion page in the workspace",
        "crud_type": "delete",
        "parameters": {
            "page_id": {
                "type": "str",
                "required": True,
                "description": "Notion page UUID to archive",
            },
        },
    }
]


def archive_page(connector: Any, user_id: str, page_id: str) -> dict[str, Any]:
    token = connector.ensure_access_token(user_id)
    body = {"archived": True}
    r = requests.patch(
        f"{NOTION_API_BASE}/pages/{page_id}",
        headers=notion_headers(token),
        json=body,
        timeout=45,
    )
    if r.status_code != 200:
        logger.warning("Notion archive page failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    if tool_name == "archive_notion_page":
        return archive_page(connector, user_id, params.get("page_id", ""))
    raise ValueError(f"Unknown delete tool: {tool_name}")
