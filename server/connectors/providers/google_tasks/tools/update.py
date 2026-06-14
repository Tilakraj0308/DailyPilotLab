"""Google Tasks — Update tools."""

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
        "name": "update_google_task",
        "description": "Update an existing task's title, notes, or completion status. Use this to mark a task as complete, rename it, or add details to it. Requires the task ID from list_google_tasks.",
        "crud_type": "update",
        "parameters": {
            "task_id": {
                "type": "str",
                "required": True,
                "description": "The ID of the task to update",
            },
            "title": {
                "type": "str",
                "required": False,
                "description": "New title for the task",
            },
            "notes": {
                "type": "str",
                "required": False,
                "description": "New notes for the task",
            },
            "completed": {
                "type": "bool",
                "required": False,
                "description": "Set to true to mark complete, false to uncomplete",
            },
            "due": {
                "type": "str",
                "required": False,
                "description": "Due date of the task in RFC 3339 format (e.g. 2023-10-25T00:00:00.000Z). The time portion is ignored by Google Tasks.",
            },
        },
    }
]


def update_task(
    connector: Any,
    user_id: str,
    task_list_id: str,
    task_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Patch a task."""
    token = connector.ensure_access_token(user_id)
    tid = urllib.parse.quote(task_id, safe="")
    lid = urllib.parse.quote(task_list_id, safe="")
    r = requests.patch(
        f"{TASKS_API_BASE}/lists/{lid}/tasks/{tid}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    if r.status_code != 200:
        logger.warning("patch task failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def execute(connector: Any, user_id: str, tool_name: str, params: dict) -> Any:
    """Route an update tool call."""
    if tool_name == "update_google_task":
        resource = db.get_connector_resource(user_id, "google_tasks", "task_list")
        if not resource or not resource[0]:
            raise ValueError("No task list selected. Please select a task list first.")
        task_list_id = resource[0]
        task_id = params.pop("task_id")

        # Build the Google Tasks API patch body
        body: dict[str, Any] = {}
        if "title" in params:
            body["title"] = params["title"]
        if "notes" in params:
            body["notes"] = params["notes"]
        if "due" in params:
            body["due"] = params["due"]
        if "completed" in params:
            from datetime import datetime, timezone
            if params["completed"]:
                body["status"] = "completed"
                body["completed"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            else:
                body["status"] = "needsAction"
                body["completed"] = None

        return update_task(connector, user_id, task_list_id, task_id, body)

    raise ValueError(f"Unknown update tool: {tool_name}")
