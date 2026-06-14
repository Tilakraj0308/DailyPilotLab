"""Google Tasks — Read tools."""

from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import requests

from connectors import db

logger = logging.getLogger(__name__)

TASKS_API_BASE = "https://tasks.googleapis.com/tasks/v1"

TOOL_DEFINITIONS = [
    {
        "name": "list_google_task_lists",
        "description": "List all available task lists in the user's Google Tasks account. Useful to see what categories or lists exist.",
        "crud_type": "read",
        "parameters": {},
    },
    {
        "name": "list_google_tasks",
        "description": "List tasks from the user's selected Google Tasks list. Use this when the user asks what tasks they have to do, or to find a specific task's ID.",
        "crud_type": "read",
        "parameters": {
            "show_completed": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Whether to include completed tasks",
            },
        },
    },
]


def list_task_lists(connector: Any, user_id: str) -> list[dict[str, Any]]:
    """List all task lists for this user."""
    token = connector.ensure_access_token(user_id)
    r = requests.get(
        f"{TASKS_API_BASE}/users/@me/lists",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code != 200:
        logger.warning("list tasklists failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    data = r.json()
    return data.get("items") or []


def fetch_tasks(
    connector: Any,
    user_id: str,
    task_list_id: str,
    show_completed: bool = False,
) -> list[dict[str, Any]]:
    """List tasks from a specific task list."""
    token = connector.ensure_access_token(user_id)
    params = {"showCompleted": "true" if show_completed else "false", "showHidden": "false"}
    r = requests.get(
        f"{TASKS_API_BASE}/lists/{urllib.parse.quote(task_list_id, safe='')}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=30,
    )
    if r.status_code != 200:
        logger.warning("list tasks failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    data = r.json()
    return data.get("items") or []


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    """Route a read tool call to the correct function."""
    if tool_name == "list_google_task_lists":
        return list_task_lists(connector, user_id)

    if tool_name == "list_google_tasks":
        resource = db.get_connector_resource(user_id, "google_tasks", "task_list")
        if not resource or not resource[0]:
            raise ValueError("No task list selected. Please select a task list first.")
        task_list_id = resource[0]
        return fetch_tasks(
            connector,
            user_id,
            task_list_id,
            show_completed=params.get("show_completed", False),
        )

    raise ValueError(f"Unknown read tool: {tool_name}")
