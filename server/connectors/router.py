from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from utils.auth_middleware import get_current_user

from connectors.models import (
    ConnectorDisconnectResponse,
    ConnectorListResponse,
    ConnectorStartRequest,
    ConnectorStartResponse,
    ConnectorStatusItem,
    CreateGoogleTaskRequest,
    SelectTaskListRequest,
    TaskListsResponse,
    TaskListItemOut,
    UpdateGoogleTaskRequest,
)
from pydantic import BaseModel
from connectors import db
from connectors.providers import PROVIDER_MAP
from connectors.providers.google_tasks.tools import read as tasks_read
from connectors.providers.google_tasks.tools import create as tasks_create
from connectors.providers.google_tasks.tools import update as tasks_update
from connectors.providers.google_tasks.tools import delete as tasks_delete

router = APIRouter()

@router.get("", response_model=ConnectorListResponse)
def list_connectors(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    rows = db.list_connectors_status(user_id)
    items = [
        ConnectorStatusItem(
            provider_key=r["provider_key"],
            display_name=r["display_name"],
            status=r["status"],
            scopes=list(r["scopes"] or []),
            connected_at=r["connected_at"],
            provider_email=r.get("provider_email"),
            error_message=r.get("error_message"),
            selected_resource_id=r.get("selected_resource_id"),
            selected_resource_name=r.get("selected_resource_name"),
        )
        for r in rows
    ]
    return ConnectorListResponse(connectors=items)


@router.post("/{provider}/start", response_model=ConnectorStartResponse)
def connector_start(
    provider: str,
    body: ConnectorStartRequest,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    raw_email = payload.get("email")
    login_hint = raw_email.strip() if isinstance(raw_email, str) and raw_email.strip() else None

    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")

    provider_instance = PROVIDER_MAP[provider]()
    try:
        url, state = provider_instance.build_start_authorization_url(
            user_id, body.return_to, login_hint=login_hint
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return ConnectorStartResponse(authorization_url=url, state=state)


@router.get("/{provider}/callback")
def connector_oauth_callback(provider: str, request: Request):
    """Public OAuth redirect target. Validates state and exchanges the authorization code."""
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")

    provider_instance = PROVIDER_MAP[provider]()
    q = request.query_params
    err = q.get("error")
    state = q.get("state")
    code = q.get("code")

    if err:
        url = provider_instance.oauth_error_callback(state, err)
        return RedirectResponse(url=url, status_code=302)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    
    try:
        redirect_url, _, _ = provider_instance.complete_oauth_callback(code, state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/{provider}/disconnect", response_model=ConnectorDisconnectResponse)
def connector_disconnect(provider: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")

    provider_instance = PROVIDER_MAP[provider]()
    try:
        provider_instance.revoke_and_disconnect(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return ConnectorDisconnectResponse(ok=True, provider_key=provider)


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


# ─── Tool Registry & History Endpoints ─────────────────────────────────────


@router.get("/{provider}/permissions")
def get_permissions(provider: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")
    return db.get_tool_permissions(user_id, provider)


class UpdatePermissionRequest(BaseModel):
    crud_type: str
    enabled: bool

@router.put("/{provider}/permissions", response_model=dict)
def update_permission(
    provider: str, body: UpdatePermissionRequest, payload: dict = Depends(get_current_user)
):
    user_id = payload.get("sub", "")
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")
    if body.crud_type not in ("create", "read", "update", "delete"):
        raise HTTPException(status_code=400, detail="Invalid crud_type")
        
    db.update_tool_permission(user_id, provider, body.crud_type, body.enabled)
    return {"ok": True, "crud_type": body.crud_type, "enabled": body.enabled}


@router.get("/{provider}/history")
def get_connector_history(provider: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")
    
    from connectors import history
    rows = history.get_recent_history(user_id, provider, limit=20)
    return {"items": rows}


@router.get("/{provider}/tools")
def get_available_tools(provider: str, payload: dict = Depends(get_current_user)):
    """Used by the frontend to display what tools are available."""
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")
    
    from connectors import tool_registry
    tools = tool_registry.get_provider_tools(provider)
    return {"tools": tools}

