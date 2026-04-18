"""Notion — Create tools (new page under a page or database)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from connectors.providers.notion.notion_api import NOTION_API_BASE, notion_headers

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "create_notion_page",
        "description": "Create a Notion page as a child of an existing page, or a row in a database",
        "crud_type": "create",
        "parameters": {
            "parent_type": {
                "type": "str",
                "required": True,
                "description": "Either 'page_id' or 'database_id'",
            },
            "parent_id": {
                "type": "str",
                "required": True,
                "description": "UUID of the parent page or database",
            },
            "title": {
                "type": "str",
                "required": True,
                "description": "Title text for the new page",
            },
            "database_title_property": {
                "type": "str",
                "required": False,
                "default": "Name",
                "description": "When parent is a database, the title property name (often Name or title)",
            },
        },
    }
]


def _title_property_block(title: str) -> dict[str, Any]:
    return {
        "title": [
            {
                "type": "text",
                "text": {"content": title[:2000]},
            }
        ]
    }


def create_page(
    connector: Any,
    user_id: str,
    parent_type: str,
    parent_id: str,
    title: str,
    database_title_property: str = "Name",
) -> dict[str, Any]:
    if not (parent_id or "").strip():
        raise ValueError("parent_id is required")
    if not (title or "").strip():
        raise ValueError("title is required")
    token = connector.ensure_access_token(user_id)
    pt = (parent_type or "").strip().lower()
    if pt == "page_id":
        body = {
            "parent": {"page_id": parent_id},
            "properties": {"title": _title_property_block(title)},
        }
    elif pt == "database_id":
        prop = (database_title_property or "Name").strip() or "Name"
        body = {
            "parent": {"database_id": parent_id},
            "properties": {prop: _title_property_block(title)},
        }
    else:
        raise ValueError("parent_type must be 'page_id' or 'database_id'")

    r = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=notion_headers(token),
        json=body,
        timeout=45,
    )
    if r.status_code != 200:
        logger.warning("Notion create page failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    if tool_name == "create_notion_page":
        return create_page(
            connector,
            user_id,
            parent_type=params.get("parent_type", ""),
            parent_id=params.get("parent_id", ""),
            title=params.get("title", ""),
            database_title_property=params.get("database_title_property", "Name"),
        )
    raise ValueError(f"Unknown create tool: {tool_name}")
