import base64
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from utils.auth_middleware import get_current_user

from connectors import db
from connectors.models import (
    ConnectorDisconnectResponse,
    ConnectorListResponse,
    ConnectorStartRequest,
    ConnectorStartResponse,
    ConnectorStatusItem,
    CreateGoogleTaskRequest,
    GmailDraftCreateRequest,
    GmailDraftCreateResponse,
    GmailPriorityResponse,
    GmailThreadSummaryOut,
    SelectTaskListRequest,
    TaskListsResponse,
    TaskListItemOut,
    UpdateGoogleTaskRequest,
)
from connectors.providers import PROVIDER_MAP
from connectors.providers.gmail import gmail_api
from connectors.providers.google_tasks.tools import read as tasks_read
from connectors.providers.google_tasks.tools import create as tasks_create
from connectors.providers.google_tasks.tools import update as tasks_update
from connectors.providers.google_tasks.tools import delete as tasks_delete

router = APIRouter()

GMAIL_PRIORITY_Q = "in:inbox newer_than:14d"
GMAIL_PRIORITY_MAX_THREADS = 15
_HEADER_KEYS_UI = frozenset(
    {
        "from",
        "to",
        "cc",
        "bcc",
        "subject",
        "date",
        "message-id",
        "in-reply-to",
        "references",
    }
)


def _payload_headers_subset(payload: dict | None) -> dict[str, str]:
    if not payload or "headers" not in payload:
        return {}
    out: dict[str, str] = {}
    for h in payload["headers"]:
        name = (h.get("name") or "").strip()
        if not name:
            continue
        lk = name.lower()
        if lk in _HEADER_KEYS_UI:
            out[lk] = h.get("value") or ""
    return out


def _thread_summary_from_api(raw: dict[str, object]) -> GmailThreadSummaryOut:
    tid = str(raw.get("id") or "")
    snippet = raw.get("snippet")
    snip_str = str(snippet) if isinstance(snippet, str) else None
    messages = raw.get("messages") or []
    if not isinstance(messages, list) or not messages:
        return GmailThreadSummaryOut(id=tid, snippet=snip_str)
    m0 = messages[0]
    if not isinstance(m0, dict):
        return GmailThreadSummaryOut(id=tid, snippet=snip_str)
    headers: dict[str, str] = {}
    pl = m0.get("payload")
    if isinstance(pl, dict):
        for h in pl.get("headers") or []:
            if not isinstance(h, dict):
                continue
            lk = (h.get("name") or "").lower()
            headers[lk] = h.get("value") or ""
    internal = m0.get("internalDate")
    labels = m0.get("labelIds")
    label_list = list(labels) if isinstance(labels, list) else []
    return GmailThreadSummaryOut(
        id=tid,
        snippet=snip_str,
        subject=headers.get("subject"),
        from_addr=headers.get("from"),
        internal_date_ms=str(internal) if internal is not None else None,
        label_ids=[str(x) for x in label_list],
    )


def _normalize_thread_for_ui(raw: dict[str, object]) -> dict[str, object]:
    tid = str(raw.get("id") or "")
    out_messages: list[dict[str, object]] = []
    for m in raw.get("messages") or []:
        if not isinstance(m, dict):
            continue
        pl = m.get("payload")
        pl_dict = pl if isinstance(pl, dict) else None
        out_messages.append(
            {
                "id": str(m.get("id") or ""),
                "snippet": m.get("snippet"),
                "internalDate": m.get("internalDate"),
                "labelIds": list(m.get("labelIds") or [])
                if isinstance(m.get("labelIds"), list)
                else [],
                "headers": _payload_headers_subset(pl_dict),
            }
        )
    return {
        "id": tid,
        "snippet": raw.get("snippet"),
        "historyId": raw.get("historyId"),
        "messages": out_messages,
    }


@router.get("/gmail/priority", response_model=GmailPriorityResponse)
def gmail_priority(
    max_results: int = 30,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    connector = PROVIDER_MAP["gmail"]()
    try:
        access_token = connector.ensure_access_token(user_id)
        listed = gmail_api.list_inbox_messages(
            access_token=access_token,
            max_results=max_results,
            q=GMAIL_PRIORITY_Q,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    msgs = listed.get("messages") or []
    if not isinstance(msgs, list):
        msgs = []

    thread_ids: list[str] = []
    seen: set[str] = set()
    for m in msgs:
        if not isinstance(m, dict):
            continue
        th = m.get("threadId")
        if not th or not isinstance(th, str):
            continue
        if th not in seen:
            seen.add(th)
            thread_ids.append(th)
    thread_ids = thread_ids[:GMAIL_PRIORITY_MAX_THREADS]

    items: list[GmailThreadSummaryOut] = []
    for thid in thread_ids:
        try:
            raw = gmail_api.get_thread(
                access_token=access_token,
                thread_id=thid,
                message_format="metadata",
            )
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        if isinstance(raw, dict):
            items.append(_thread_summary_from_api(raw))

    return GmailPriorityResponse(query=GMAIL_PRIORITY_Q, items=items)


@router.get("/gmail/threads/{thread_id}")
def gmail_thread_detail(thread_id: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    connector = PROVIDER_MAP["gmail"]()
    try:
        access_token = connector.ensure_access_token(user_id)
        raw = gmail_api.get_thread(
            access_token=access_token,
            thread_id=thread_id,
            message_format="metadata",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if not isinstance(raw, dict):
        raise HTTPException(status_code=502, detail="Invalid thread response")
    return _normalize_thread_for_ui(raw)


@router.post("/gmail/drafts", response_model=GmailDraftCreateResponse)
def gmail_create_draft(body: GmailDraftCreateRequest, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    connector = PROVIDER_MAP["gmail"]()
    try:
        access_token = connector.ensure_access_token(user_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    msg = EmailMessage()
    msg["Subject"] = body.subject
    if body.to:
        msg["To"] = ", ".join(body.to)
    if body.cc:
        msg["Cc"] = ", ".join(body.cc)
    if body.bcc:
        msg["Bcc"] = ", ".join(body.bcc)
    msg.set_content(body.body_text)
    raw_bytes = msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")

    api_body: dict = {"message": {"raw": raw_b64}}
    if body.thread_id:
        api_body["message"]["threadId"] = body.thread_id

    try:
        created = gmail_api.create_draft(access_token=access_token, body=api_body)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    if not isinstance(created, dict):
        raise HTTPException(status_code=502, detail="Invalid draft response")
    draft_id = str(created.get("id") or "")
    inner = created.get("message")
    message_id = None
    out_thread_id = None
    if isinstance(inner, dict):
        mid = inner.get("id")
        if mid is not None:
            message_id = str(mid)
        tid = inner.get("threadId")
        if tid is not None:
            out_thread_id = str(tid)
    return GmailDraftCreateResponse(
        draft_id=draft_id,
        message_id=message_id,
        thread_id=out_thread_id,
    )


@router.post("/gmail/drafts/{draft_id}/send")
def gmail_send_draft(draft_id: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    connector = PROVIDER_MAP["gmail"]()
    try:
        access_token = connector.ensure_access_token(user_id)
        sent = gmail_api.send_draft(access_token=access_token, draft_id=draft_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if not isinstance(sent, dict):
        raise HTTPException(status_code=502, detail="Invalid send response")
    return {"ok": True, "id": str(sent.get("id") or "")}


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

