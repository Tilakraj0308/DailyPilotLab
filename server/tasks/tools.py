"""
tasks/tools.py — LLM tool definitions and executor for the tasks module.

These tools are always injected into the agent (no OAuth gate required).
The executor is a lightweight wrapper around tasks.service — no connector
auth or permission lookup needed.
"""
from __future__ import annotations

import logging

from tasks import service

logger = logging.getLogger(__name__)

# ── Constant used by chat_service to identify task tools ────────────────────

TASK_TOOL_NAMES: set[str] = {"get_tasks", "create_task", "update_task"}

# ── Tool definitions (OpenAI function-calling schema) ────────────────────────

TASK_TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "get_tasks",
        "description": (
            "Read the user's tasks with a preset filter. "
            "Use this whenever the user asks about their to-dos, tasks, or plans. "
            "Available filters: "
            "'all' – every active task; "
            "'due_today' – tasks due today; "
            "'in_progress' – tasks currently being worked on; "
            "'high_priority' – high or urgent tasks; "
            "'overdue' – tasks past their due date that aren't done; "
            "'completed' – finished tasks."
        ),
        "parameters": {
            "filter": {
                "type": "str",
                "description": "One of: all, due_today, in_progress, high_priority, overdue, completed",
                "required": True,
            }
        },
        "crud_type": "read",
    },
    {
        "name": "create_task",
        "description": (
            "Create a new task for the user. "
            "Use this when the user asks to add, create, or schedule a to-do item."
        ),
        "parameters": {
            "title": {
                "type": "str",
                "description": "Short title for the task.",
                "required": True,
            },
            "description": {
                "type": "str",
                "description": "Optional longer description or notes.",
                "required": False,
            },
            "priority": {
                "type": "str",
                "description": "One of: low, medium, high, urgent. Defaults to medium.",
                "required": False,
            },
            "due_date": {
                "type": "str",
                "description": "ISO 8601 datetime string for the due date/time (e.g. 2026-09-10T18:00:00Z). Optional.",
                "required": False,
            },
        },
        "crud_type": "create",
    },
    {
        "name": "update_task",
        "description": (
            "Update an existing task — change its status, priority, due date, or title. "
            "Use this when the user says a task is done, wants to reschedule it, "
            "change its priority, or mark it as in progress."
        ),
        "parameters": {
            "task_id": {
                "type": "str",
                "description": "The UUID of the task to update (from get_tasks results).",
                "required": True,
            },
            "status": {
                "type": "str",
                "description": "New status: todo, in_progress, done, or cancelled.",
                "required": False,
            },
            "priority": {
                "type": "str",
                "description": "New priority: low, medium, high, or urgent.",
                "required": False,
            },
            "due_date": {
                "type": "str",
                "description": "New due date as ISO 8601 string.",
                "required": False,
            },
            "title": {
                "type": "str",
                "description": "Updated title.",
                "required": False,
            },
        },
        "crud_type": "update",
    },
]


# ── Executor ─────────────────────────────────────────────────────────────────

def execute_task_tool(user_id: str, tool_name: str, params: dict) -> dict:
    """
    Route a task tool call to the service layer.
    Returns a plain dict — the same shape as connector tool results so
    chat_service can handle it uniformly.
    """
    try:
        if tool_name == "get_tasks":
            tasks = service.get_tasks(user_id, filter_key=params.get("filter", "all"))
            return {"ok": True, "tasks": tasks, "count": len(tasks)}

        elif tool_name == "create_task":
            task = service.create_task(user_id, params)
            return {"ok": True, "task": task}

        elif tool_name == "update_task":
            task_id = params.pop("task_id")
            task = service.update_task(user_id, task_id, params)
            return {"ok": True, "task": task}

        else:
            return {"ok": False, "error": f"Unknown task tool: {tool_name}"}

    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error("Task tool '%s' failed: %s", tool_name, e, exc_info=True)
        return {"ok": False, "error": str(e)}
