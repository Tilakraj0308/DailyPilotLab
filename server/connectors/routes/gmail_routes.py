from __future__ import annotations

import base64
import json
import logging
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException

from connectors.models import (
    GmailAiDraftSuggestionOut,
    GmailAiSuggestReplyRequest,
    GmailDraftCreateRequest,
    GmailDraftCreateResponse,
    GmailPriorityResponse,
    GmailThreadSummaryOut,
)
from connectors.providers import PROVIDER_MAP
from connectors.providers.gmail import gmail_api
from connectors.providers.gmail.thread_helpers import (
    GMAIL_DEFAULT_PRIORITY_Q,
    fetch_priority_threads,
    normalize_thread_detail_dict,
)
from connectors.routes.gmail_common import (
    _GMAIL_AI_REPLY_SYSTEM,
    log_gmail_ui_tool,
    map_gmail_upstream_exc,
    require_gmail_tool_permission,
)
from utils.auth_middleware import get_current_user
from utils.openAi import openai_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/gmail/priority", response_model=GmailPriorityResponse)
def gmail_priority(
    max_results: int = 30,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    require_gmail_tool_permission(user_id, "read", feature="Gmail priority inbox")
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
        raise map_gmail_upstream_exc(e) from e

    items = [GmailThreadSummaryOut(**x) for x in result["items"]]
    return GmailPriorityResponse(query=result["query"], items=items)


@router.get("/gmail/threads/{thread_id}")
def gmail_thread_detail(thread_id: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    require_gmail_tool_permission(user_id, "read", feature="Gmail thread detail")
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
        raise map_gmail_upstream_exc(e) from e
    if not isinstance(raw, dict):
        raise HTTPException(status_code=502, detail="Invalid thread response")
    return normalize_thread_detail_dict(raw)


@router.post("/gmail/ai/suggest-reply", response_model=GmailAiDraftSuggestionOut)
def gmail_ai_suggest_reply(
    body: GmailAiSuggestReplyRequest,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    require_gmail_tool_permission(
        user_id, "create", feature="Gmail AI suggest-reply"
    )
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
        raise map_gmail_upstream_exc(e) from e
    if not isinstance(raw, dict):
        raise HTTPException(status_code=502, detail="Invalid thread response")
    normalized = normalize_thread_detail_dict(raw)
    user_prompt = json.dumps(normalized, indent=2, default=str)

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
    require_gmail_tool_permission(user_id, "create", feature="Gmail create draft")
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
        raise map_gmail_upstream_exc(e) from e

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
    log_gmail_ui_tool(
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
    require_gmail_tool_permission(user_id, "update", feature="Gmail send draft")
    connector = PROVIDER_MAP["gmail"]()
    try:
        access_token = connector.ensure_access_token(user_id)
        sent = gmail_api.send_draft(access_token=access_token, draft_id=draft_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise map_gmail_upstream_exc(e) from e
    if not isinstance(sent, dict):
        raise HTTPException(status_code=502, detail="Invalid send response")
    sent_id = str(sent.get("id") or "")
    thread_after = sent.get("threadId")
    thread_str = str(thread_after) if thread_after is not None else None
    log_gmail_ui_tool(
        user_id,
        tool_name="gmail_ui_send_draft",
        crud_type="update",
        params={"draft_id": draft_id, "thread_id": thread_str},
        result_summary={"message_id": sent_id, "thread_id": thread_str},
    )
    return {"ok": True, "id": sent_id}
