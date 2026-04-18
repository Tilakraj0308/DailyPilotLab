import base64
import json
import logging
from email.message import EmailMessage

import requests.exceptions
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from utils.auth_middleware import get_current_user

from connectors import db
from connectors import history
from connectors.models import (
    ConnectorDisconnectResponse,
    ConnectorListResponse,
    ConnectorStartRequest,
    ConnectorStartResponse,
    ConnectorStatusItem,
    CreateGoogleTaskRequest,
    GmailAiDraftSuggestionOut,
    GmailAiSuggestReplyRequest,
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
from connectors.providers.gmail.thread_helpers import (
    GMAIL_DEFAULT_PRIORITY_Q,
    fetch_priority_threads,
    normalize_thread_detail_dict,
)
from connectors.providers.google_tasks.tools import read as tasks_read
from connectors.providers.google_tasks.tools import create as tasks_create
from connectors.providers.google_tasks.tools import update as tasks_update
from connectors.providers.google_tasks.tools import delete as tasks_delete

router = APIRouter()

_GMAIL_AI_REPLY_SYSTEM = (
    "You draft email replies only. Output must follow the required JSON schema. "
    "Write a polite, concise reply body the user can paste into Gmail. "
    "Do not include instructions about sending, clicking send, or using the UI. "
    "Do not claim the message was sent. "
    "Optional subject: only if a clearer subject helps; otherwise omit or null."
)
logger = logging.getLogger(__name__)


def _map_gmail_upstream_exc(exc: BaseException) -> HTTPException:
    """Map Gmail HTTP client failures to API responses (404 when resource missing)."""
    if isinstance(exc, requests.exceptions.HTTPError):
        if exc.response is not None and exc.response.status_code == 404:
            return HTTPException(status_code=404, detail="Gmail resource not found")
        return HTTPException(status_code=502, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


def _log_gmail_ui_tool(
    user_id: str,
    *,
    tool_name: str,
    crud_type: str,
    params: dict[str, object | None],
    result_summary: dict[str, object],
) -> None:
    clean_params = {k: v for k, v in params.items() if v is not None}
    clean_summary = {k: v for k, v in result_summary.items() if v is not None}
    try:
        history.log_tool_call(
            user_id=user_id,
            provider_key="gmail",
            tool_name=tool_name,
            crud_type=crud_type,
            params=clean_params or None,
            result_summary=clean_summary or None,
            status="success",
            error_message=None,
            triggered_by="user",
            ai_tool_response=None,
        )
    except Exception as e:
        logger.warning("Failed to log gmail UI tool history: %s", e)


@router.get("/gmail/priority", response_model=GmailPriorityResponse)
def gmail_priority(
    max_results: int = 30,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    connector = PROVIDER_MAP["gmail"]()
    try:
        access_token = connector.ensure_access_token(user_id)
        result = fetch_priority_threads(
            access_token=access_token,
            max_results=max_results,
            q=GMAIL_DEFAULT_PRIORITY_Q,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise _map_gmail_upstream_exc(e) from e

    items = [GmailThreadSummaryOut(**x) for x in result["items"]]
    return GmailPriorityResponse(query=result["query"], items=items)


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
        raise _map_gmail_upstream_exc(e) from e
    if not isinstance(raw, dict):
        raise HTTPException(status_code=502, detail="Invalid thread response")
    return normalize_thread_detail_dict(raw)


@router.post("/gmail/ai/suggest-reply", response_model=GmailAiDraftSuggestionOut)
def gmail_ai_suggest_reply(
    body: GmailAiSuggestReplyRequest,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    connector = PROVIDER_MAP["gmail"]()
    try:
        access_token = connector.ensure_access_token(user_id)
        raw = gmail_api.get_thread(
            access_token=access_token,
            thread_id=body.thread_id,
            message_format="metadata",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise _map_gmail_upstream_exc(e) from e
    if not isinstance(raw, dict):
        raise HTTPException(status_code=502, detail="Invalid thread response")
    normalized = normalize_thread_detail_dict(raw)
    user_prompt = json.dumps(normalized, indent=2, default=str)
    from utils.openAi import openai_client

    try:
        parsed = openai_client.get_chat_completion(
            system_prompt=_GMAIL_AI_REPLY_SYSTEM,
            user_prompt=user_prompt,
            response_format=GmailAiDraftSuggestionOut,
        )
    except Exception as e:
        logger.exception("Gmail AI suggest-reply failed")
        raise HTTPException(status_code=502, detail=f"AI draft failed: {e!s}") from e
    if parsed is None:
        raise HTTPException(status_code=502, detail="AI returned no draft")
    if not (parsed.body_text or "").strip():
        raise HTTPException(status_code=502, detail="AI returned an empty body")
    return GmailAiDraftSuggestionOut(
        subject=parsed.subject,
        body_text=parsed.body_text.strip(),
    )


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
        raise _map_gmail_upstream_exc(e) from e

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
    _log_gmail_ui_tool(
        user_id,
        tool_name="gmail_ui_create_draft",
        crud_type="create",
        params={
            "thread_id": body.thread_id,
            "draft_id": draft_id or None,
            "message_id": message_id,
        },
        result_summary={
            "draft_id": draft_id,
            "thread_id": out_thread_id,
            "message_id": message_id,
        },
    )
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
        raise _map_gmail_upstream_exc(e) from e
    if not isinstance(sent, dict):
        raise HTTPException(status_code=502, detail="Invalid send response")
    sent_id = str(sent.get("id") or "")
    thread_after = sent.get("threadId")
    thread_str = str(thread_after) if thread_after is not None else None
    _log_gmail_ui_tool(
        user_id,
        tool_name="gmail_ui_send_draft",
        crud_type="update",
        params={"draft_id": draft_id, "thread_id": thread_str},
        result_summary={"message_id": sent_id, "thread_id": thread_str},
    )
    return {"ok": True, "id": sent_id}


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

