"""
tasks/router.py — FastAPI routes for task CRUD.

Mounted at /tasks in server.py.
All routes require a valid Supabase JWT (via get_current_user dependency).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from utils.auth_middleware import get_current_user
from tasks import service

router = APIRouter()


# ── Pydantic models ─────────────────────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    due_date: str | None = None   # ISO 8601 string, nullable


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None   # pass explicit None to clear the due date


# ── Routes ──────────────────────────────────────────────────────────────────

@router.get("")
def list_tasks(filter: str = "all", payload: dict = Depends(get_current_user)):
    """
    List tasks for the authenticated user.

    Query param `filter` accepts:
      all | due_today | in_progress | high_priority | overdue | completed
    """
    user_id = payload["sub"]
    try:
        tasks = service.get_tasks(user_id, filter_key=filter)
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201)
def create_task(req: TaskCreateRequest, payload: dict = Depends(get_current_user)):
    """Create a new task."""
    user_id = payload["sub"]
    try:
        task = service.create_task(user_id, req.model_dump(exclude_none=True))
        return {"task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{task_id}")
def update_task(task_id: str, req: TaskUpdateRequest, payload: dict = Depends(get_current_user)):
    """Partially update a task (title, description, status, priority, due_date)."""
    user_id = payload["sub"]
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    try:
        task = service.update_task(user_id, task_id, updates)
        return {"task": task}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
def delete_task(task_id: str, payload: dict = Depends(get_current_user)):
    """Soft-delete a task by setting its status to 'cancelled'."""
    user_id = payload["sub"]
    try:
        task = service.delete_task(user_id, task_id)
        return {"task": task, "message": "Task cancelled."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
