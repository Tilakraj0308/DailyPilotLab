"""Notion — Read tools (search pages)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from connectors.providers.notion.notion_api import NOTION_API_BASE, notion_headers

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "search_notion_pages",
        "description": "Search pages and databases in the connected Notion workspace. Use this when the user asks to find a document, read notes, or search for information in Notion.",
        "crud_type": "read",
        "parameters": {
            "query": {
                "type": "str",
                "required": False,
                "default": "",
                "description": "Search query text (empty returns recent results)",
            },
            "page_size": {
                "type": "int",
                "required": False,
                "default": 10,
                "description": "Max results (1-100)",
            },
        },
    }
]


def search_pages(
    connector: Any,
    user_id: str,
    query: str = "",
    page_size: int = 10,
) -> dict[str, Any]:
    token = connector.ensure_access_token(user_id)
    size = max(1, min(100, int(page_size)))
    body: dict[str, Any] = {"page_size": size}
    if query and query.strip():
        body["query"] = query.strip()
    r = requests.post(
        f"{NOTION_API_BASE}/search",
        headers=notion_headers(token),
        json=body,
        timeout=45,
    )
    if r.status_code != 200:
        logger.warning("Notion search failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    if tool_name == "search_notion_pages":
        return search_pages(
            connector,
            user_id,
            query=params.get("query") or "",
            page_size=params.get("page_size", 10),
        )
    raise ValueError(f"Unknown read tool: {tool_name}")
