"""
Tool Registry — discovers available tools from connected providers.

Scans each provider's `tools/` package, collects TOOL_DEFINITIONS,
and filters by the user's connected providers and permission toggles.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from connectors import db
from connectors.providers import PROVIDER_MAP

logger = logging.getLogger(__name__)

# Cache: provider_key → list of tool definitions
_TOOL_CACHE: dict[str, list[dict]] = {}

def _load_tools_for_provider(provider_key: str) -> list[dict]:
    """Import and cache the TOOL_DEFINITIONS from a provider's tools package."""
    if provider_key in _TOOL_CACHE:
        return _TOOL_CACHE[provider_key]

    try:
        mod = importlib.import_module(f"connectors.providers.{provider_key}.tools")
        defs = getattr(mod, "TOOL_DEFINITIONS", [])
        # Tag each definition with its provider
        for d in defs:
            d.setdefault("provider_key", provider_key)
        _TOOL_CACHE[provider_key] = defs
        return defs
    except (ImportError, AttributeError) as e:
        logger.warning("Could not load tools for %s: %s", provider_key, e)
        return []


def get_all_tool_definitions() -> list[dict]:
    """Return every registered tool across all providers (ignoring user context)."""
    all_tools: list[dict] = []
    for provider_key in PROVIDER_MAP:
        all_tools.extend(_load_tools_for_provider(provider_key))
    return all_tools


def get_user_tools(user_id: str) -> list[dict]:
    """
    Return tool definitions for providers the user has connected,
    filtered by the user's CRUD permission toggles.
    """
    connected = db.list_connected_providers(user_id)
    tools: list[dict] = []

    for provider_key in connected:
        provider_tools = _load_tools_for_provider(provider_key)
        permissions = db.get_tool_permissions(user_id, provider_key)

        for tool in provider_tools:
            crud = tool.get("crud_type", "read")
            # Default: all enabled if no permissions row exists yet
            if permissions.get(crud, True):
                tools.append(tool)

    return tools


def get_provider_tools(provider_key: str) -> list[dict]:
    """Return tool definitions for a single provider."""
    return _load_tools_for_provider(provider_key)


def resolve_tool(tool_name: str) -> tuple[str, dict] | None:
    """
    Given a tool name, find which provider it belongs to.
    Returns (provider_key, tool_definition) or None.
    """
    for provider_key in PROVIDER_MAP:
        for tool in _load_tools_for_provider(provider_key):
            if tool["name"] == tool_name:
                return provider_key, tool
    return None
