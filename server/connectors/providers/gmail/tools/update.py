"""Gmail — Update tools (no agent-callable tools; send uses HTTP only)."""

from __future__ import annotations

from typing import Any

TOOL_DEFINITIONS: list[dict] = []


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    raise ValueError(f"Unknown update tool: {tool_name}")
