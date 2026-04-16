"""Google Tasks — Delete tools."""

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
        "name": "delete_google_task",
        "description": "Delete a task from the user's Google Tasks list",
        "crud_type": "delete",
        "parameters": {
            "task_id": {
                "type": "str",
                "required": True,
                "description": "The ID of the task to delete",
            },
        },
    }
]


def delete_task(
    connector: Any,
    user_id: str,
    task_list_id: str,
    task_id: str,
) -> None:
    """Delete a task from a list."""
    token = connector.ensure_access_token(user_id)
    tid = urllib.parse.quote(task_id, safe="")
    lid = urllib.parse.quote(task_list_id, safe="")
    r = requests.delete(
        f"{TASKS_API_BASE}/lists/{lid}/tasks/{tid}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code not in (200, 204):
        logger.warning("delete task failed: %s %s", r.status_code, r.text)
        r.raise_for_status()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    """Route a delete tool call."""
    if tool_name == "delete_google_task":
        resource = db.get_connector_resource(user_id, "google_tasks", "task_list")
        if not resource or not resource[0]:
            raise ValueError("No task list selected. Please select a task list first.")
        task_list_id = resource[0]
        delete_task(connector, user_id, task_list_id, task_id=params["task_id"])
        return {"ok": True, "task_id": params["task_id"]}

    raise ValueError(f"Unknown delete tool: {tool_name}")
