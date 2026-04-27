from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from connectors import db
from connectors.models import (
    ConnectorDisconnectResponse,
    ConnectorListResponse,
    ConnectorStartRequest,
    ConnectorStartResponse,
    ConnectorStatusItem,
)
from connectors.providers import PROVIDER_MAP
from services.auth_service import get_or_create_user
from utils.auth_middleware import get_current_user

router = APIRouter()


# Path must not be empty on a sub-router (FastAPI include_router restriction).
@router.get("/", response_model=ConnectorListResponse)
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

    if provider == "notion" and user_id and login_hint:
        meta = payload.get("user_metadata") or {}
        if not isinstance(meta, dict):
            meta = {}
        nm = meta.get("full_name") or meta.get("name")
        av = meta.get("avatar_url")
        get_or_create_user(
            user_id,
            login_hint,
            nm if isinstance(nm, str) else None,
            av if isinstance(av, str) else None,
        )

    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")

    if not db.connector_provider_exists(provider):
        raise HTTPException(
            status_code=503,
            detail=(
                f"Connector '{provider}' is implemented in the API but not registered in Postgres "
                f"table public.connector_providers (OAuth cannot start until it exists). "
                f"Apply Supabase migrations — for Gmail run migration "
                f"`supabase/migrations/20260418150000_gmail_connector_provider.sql` "
                f"(e.g. `npx supabase db push` from the repo root), or insert the row manually, then retry."
            ),
        )

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
