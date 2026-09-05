"""
tasks/db.py — raw psycopg2 queries for the tasks table.

All functions accept user_id (auth_id) for tenant isolation.
Uses the shared get_dict_cursor() context manager from db.dbConnection.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from db.dbConnection import get_dict_cursor

logger = logging.getLogger(__name__)


def list_tasks(user_id: str, filters: dict | None = None) -> list[dict]:
    """
    Fetch tasks for a user with optional filters.

    Supported filter keys:
      status         – exact task_status value
      priority       – list of task_priority values (IN clause)
      due_before     – ISO string (inclusive upper bound on due_date)
      due_after      – ISO string (inclusive lower bound on due_date)
      exclude_status – status value to exclude
    """
    conditions = ["user_id = %s"]
    values: list[Any] = [user_id]

    if filters:
        if "status" in filters:
            conditions.append("status = %s::task_status")
            values.append(filters["status"])
        if "exclude_status" in filters:
            conditions.append("status != %s::task_status")
            values.append(filters["exclude_status"])
        if "priority" in filters:
            conditions.append("priority = ANY(%s::task_priority[])")
            values.append(filters["priority"])
        if "due_before" in filters:
            conditions.append("due_date <= %s")
            values.append(filters["due_before"])
        if "due_after" in filters:
            conditions.append("due_date >= %s")
            values.append(filters["due_after"])

    where = " AND ".join(conditions)
    query = f"SELECT * FROM tasks WHERE {where} ORDER BY created_at DESC"

    with get_dict_cursor() as cur:
        cur.execute(query, tuple(values))
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_task(user_id: str, task_id: str) -> dict:
    """Fetch a single task. Raises ValueError if not found or not owned by user."""
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT * FROM tasks WHERE id = %s AND user_id = %s",
            (task_id, user_id),
        )
        row = cur.fetchone()
    if not row:
        raise ValueError(f"Task {task_id} not found.")
    return dict(row)


def create_task(user_id: str, data: dict) -> dict:
    """Insert a new task row and return the full created record."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO tasks (user_id, title, description, status, priority, due_date)
            VALUES (%s, %s, %s, %s::task_status, %s::task_priority, %s)
            RETURNING *
            """,
            (
                user_id,
                data["title"],
                data.get("description"),
                data.get("status", "todo"),
                data.get("priority", "medium"),
                data.get("due_date"),
            ),
        )
        return dict(cur.fetchone())


def update_task(user_id: str, task_id: str, data: dict) -> dict:
    """
    Partial update. Automatically sets completed_at when status → 'done',
    and clears it when transitioning away. Raises ValueError if not found.
    """
    get_task(user_id, task_id)  # ownership check

    allowed = {"title", "description", "status", "priority", "due_date", "completed_at"}
    payload: dict[str, Any] = {k: v for k, v in data.items() if k in allowed}

    if "status" in payload:
        if payload["status"] == "done":
            payload["completed_at"] = datetime.now(timezone.utc)
        else:
            payload["completed_at"] = None

    if not payload:
        return get_task(user_id, task_id)

    # Build SET clause — cast enum columns explicitly so psycopg2 text binds work
    ENUM_CASTS = {"status": "::task_status", "priority": "::task_priority"}
    set_clauses = [f"{col} = %s{ENUM_CASTS.get(col, '')}" for col in payload.keys()]
    values = list(payload.values()) + [task_id, user_id]

    query = (
        f"UPDATE tasks SET {', '.join(set_clauses)} "
        f"WHERE id = %s AND user_id = %s RETURNING *"
    )

    with get_dict_cursor() as cur:
        cur.execute(query, tuple(values))
        return dict(cur.fetchone())


def delete_task(user_id: str, task_id: str) -> dict:
    """Soft-delete: set status to 'cancelled'."""
    return update_task(user_id, task_id, {"status": "cancelled"})
