"""
tasks/service.py — business logic and filter helpers for the tasks module.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from tasks import db


# ── Private filter helpers ──────────────────────────────────────────────────

def _due_today(user_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return db.list_tasks(user_id, {
        "due_after": start.isoformat(),
        "due_before": end.isoformat(),
        "exclude_status": "cancelled",
    })


def _overdue(user_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    tasks = db.list_tasks(user_id, {
        "due_before": now.isoformat(),
        "exclude_status": "cancelled",
    })
    return [t for t in tasks if t["status"] != "done"]


# ── Filter map (defined after helpers) ─────────────────────────────────────

FILTER_MAP = {
    "all":           lambda uid: db.list_tasks(uid, {"exclude_status": "cancelled"}),
    "due_today":     _due_today,
    "in_progress":   lambda uid: db.list_tasks(uid, {"status": "in_progress"}),
    "high_priority": lambda uid: db.list_tasks(uid, {"priority": ["high", "urgent"], "exclude_status": "cancelled"}),
    "overdue":       _overdue,
    "completed":     lambda uid: db.list_tasks(uid, {"status": "done"}),
}


# ── Public service API ──────────────────────────────────────────────────────

def get_tasks(user_id: str, filter_key: str = "all") -> list[dict]:
    """Return tasks for user using the named filter preset."""
    fn = FILTER_MAP.get(filter_key, FILTER_MAP["all"])
    return fn(user_id)


def create_task(user_id: str, data: dict) -> dict:
    return db.create_task(user_id, data)


def update_task(user_id: str, task_id: str, data: dict) -> dict:
    return db.update_task(user_id, task_id, data)


def delete_task(user_id: str, task_id: str) -> dict:
    return db.delete_task(user_id, task_id)


def get_task(user_id: str, task_id: str) -> dict:
    return db.get_task(user_id, task_id)
