"""Notion — Update tools (page title / properties)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from connectors.providers.notion.notion_api import NOTION_API_BASE, notion_headers

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "update_notion_page",
        "description": "Update a Notion page title (default title property) or merge additional properties",
        "crud_type": "update",
        "parameters": {
            "page_id": {
                "type": "str",
                "required": True,
                "description": "Notion page UUID",
            },
            "title": {
                "type": "str",
                "required": False,
                "description": "New title (updates default title property)",
            },
            "title_property_name": {
                "type": "str",
                "required": False,
                "default": "title",
                "description": "Property name for the title (often 'title' for pages)",
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


def update_page(
    connector: Any,
    user_id: str,
    page_id: str,
    title: str | None = None,
    title_property_name: str = "title",
) -> dict[str, Any]:
    token = connector.ensure_access_token(user_id)
    properties: dict[str, Any] = {}
    if title is not None and str(title).strip() != "":
        prop = (title_property_name or "title").strip() or "title"
        properties[prop] = _title_property_block(str(title))

    if not properties:
        raise ValueError("title is required to update a page")

    body: dict[str, Any] = {"properties": properties}
    r = requests.patch(
        f"{NOTION_API_BASE}/pages/{page_id}",
        headers=notion_headers(token),
        json=body,
        timeout=45,
    )
    if r.status_code != 200:
        logger.warning("Notion update page failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    if tool_name == "update_notion_page":
        return update_page(
            connector,
            user_id,
            page_id=params.get("page_id", ""),
            title=params.get("title"),
            title_property_name=params.get("title_property_name", "title"),
        )
    raise ValueError(f"Unknown update tool: {tool_name}")
