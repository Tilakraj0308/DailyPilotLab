"""Shared Notion REST API helpers for tools."""

from __future__ import annotations

from connectors.oauth_common import env

NOTION_API_BASE = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2022-06-28"


def notion_version() -> str:
    return env("NOTION_API_VERSION", DEFAULT_NOTION_VERSION) or DEFAULT_NOTION_VERSION


def notion_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": notion_version(),
    }
