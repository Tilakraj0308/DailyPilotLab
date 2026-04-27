from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from connectors import db
from connectors import history
from connectors import tool_registry
from connectors.providers import PROVIDER_MAP
from utils.auth_middleware import get_current_user

router = APIRouter()


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

    rows = history.get_recent_history(user_id, provider, limit=20)
    return {"items": rows}


@router.get("/{provider}/tools")
def get_available_tools(provider: str, payload: dict = Depends(get_current_user)):
    """Used by the frontend to display what tools are available."""
    if provider not in PROVIDER_MAP:
        raise HTTPException(status_code=404, detail="Unknown connector provider")

    tools = tool_registry.get_provider_tools(provider)
    return {"tools": tools}
