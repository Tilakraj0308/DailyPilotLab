from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from connectors import db
from connectors.models import (
    CreateGoogleTaskRequest,
    SelectTaskListRequest,
    TaskListsResponse,
    TaskListItemOut,
    UpdateGoogleTaskRequest,
)
from connectors.providers import PROVIDER_MAP
from connectors.providers.google_tasks.tools import read as tasks_read
from connectors.providers.google_tasks.tools import create as tasks_create
from connectors.providers.google_tasks.tools import update as tasks_update
from connectors.providers.google_tasks.tools import delete as tasks_delete
from utils.auth_middleware import get_current_user

router = APIRouter()


@router.get("/google_tasks/lists", response_model=TaskListsResponse)
def google_tasks_list_tasklists(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    connector = PROVIDER_MAP["google_tasks"]()
    try:
        raw = tasks_read.list_task_lists(connector, user_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    items = [TaskListItemOut(id=x["id"], title=x.get("title") or "") for x in raw]
    return TaskListsResponse(items=items)


@router.post("/google_tasks/select-list")
def google_tasks_select_list(body: SelectTaskListRequest, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    try:
        db.upsert_selected_task_list(
            user_id,
            "google_tasks",
            body.task_list_id,
            body.task_list_title,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.get("/google_tasks/tasks")
def google_tasks_list_tasks(
    show_completed: bool = False,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    task_list_id, _ = db.get_connector_resource(
        user_id, "google_tasks", "task_list"
    )
    if not task_list_id:
        raise HTTPException(status_code=400, detail="No task list selected")

    connector = PROVIDER_MAP["google_tasks"]()
    try:
        tasks = tasks_read.fetch_tasks(connector, user_id, task_list_id, show_completed=show_completed)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"items": tasks}


@router.post("/google_tasks/tasks")
def google_tasks_create_task(body: CreateGoogleTaskRequest, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    task_list_id, _ = db.get_connector_resource(
        user_id, "google_tasks", "task_list"
    )
    if not task_list_id:
        raise HTTPException(status_code=400, detail="No task list selected")

    connector = PROVIDER_MAP["google_tasks"]()
    try:
        task = tasks_create.create_task(connector, user_id, task_list_id, body.title, body.notes)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return task


@router.patch("/google_tasks/tasks/{task_id}")
def google_tasks_update_task(
    task_id: str,
    body: UpdateGoogleTaskRequest,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    task_list_id, _ = db.get_connector_resource(
        user_id, "google_tasks", "task_list"
    )
    if not task_list_id:
        raise HTTPException(status_code=400, detail="No task list selected")
    patch: dict = {}
    if body.title is not None:
        patch["title"] = body.title
    if body.notes is not None:
        patch["notes"] = body.notes
    if body.status is not None:
        patch["status"] = body.status
    elif body.completed is True:
        patch["status"] = "completed"
    elif body.completed is False:
        patch["status"] = "needsAction"
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    connector = PROVIDER_MAP["google_tasks"]()
    try:
        task = tasks_update.update_task(connector, user_id, task_list_id, task_id, patch)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return task


@router.delete("/google_tasks/tasks/{task_id}")
def google_tasks_delete_task(task_id: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    task_list_id, _ = db.get_connector_resource(
        user_id, "google_tasks", "task_list"
    )
    if not task_list_id:
        raise HTTPException(status_code=400, detail="No task list selected")

    connector = PROVIDER_MAP["google_tasks"]()
    try:
        tasks_delete.delete_task(connector, user_id, task_list_id, task_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"ok": True}
