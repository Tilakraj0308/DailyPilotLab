"""Google Tasks — Create tools."""

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
        "name": "create_google_task",
        "description": "Create a new task in the user's selected Google Tasks list",
        "crud_type": "create",
        "parameters": {
            "title": {
                "type": "str",
                "required": True,
                "description": "Title of the task",
            },
            "notes": {
                "type": "str",
                "required": False,
                "description": "Optional notes or description for the task",
            },
        },
    }
]


def create_task(
    connector: Any,
    user_id: str,
    task_list_id: str,
    title: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create a new task in the given list."""
    token = connector.ensure_access_token(user_id)
    body: dict[str, Any] = {"title": title}
    if notes:
        body["notes"] = notes
    r = requests.post(
        f"{TASKS_API_BASE}/lists/{urllib.parse.quote(task_list_id, safe='')}/tasks",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    if r.status_code not in (200, 201):
        logger.warning("create task failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    """Route a create tool call."""
    if tool_name == "create_google_task":
        resource = db.get_connector_resource(user_id, "google_tasks", "task_list")
        if not resource or not resource[0]:
            raise ValueError("No task list selected. Please select a task list first.")
        task_list_id = resource[0]
        return create_task(
            connector,
            user_id,
            task_list_id,
            title=params["title"],
            notes=params.get("notes"),
        )

    raise ValueError(f"Unknown create tool: {tool_name}")
