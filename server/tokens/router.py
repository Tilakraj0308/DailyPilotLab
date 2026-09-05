"""
FastAPI Router for Token Usage Traceability & Analytics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from utils.auth_middleware import get_current_user
from .tracker import TokenTracker

router = APIRouter()

@router.get("/stats")
def get_token_stats(payload: dict = Depends(get_current_user)):
    """
    Get aggregated token usage statistics for the current user.
    """
    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
        
    stats = TokenTracker.get_user_stats(user_id)
    return {"status": "success", "data": stats}

@router.get("/traces")
def get_token_traces(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request_type: Optional[str] = Query(None),
    payload: dict = Depends(get_current_user)
):
    """
    Get paginated token request traces for the current user.
    """
    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
        
    traces = TokenTracker.get_user_traces(
        user_id=user_id,
        limit=limit,
        offset=offset,
        request_type=request_type
    )
    return {"status": "success", "traces": traces, "limit": limit, "offset": offset}

@router.get("/traces/{trace_id}")
def get_token_trace_timeline(
    trace_id: str,
    payload: dict = Depends(get_current_user)
):
    """
    Get step-by-step timeline details for a specific request trace.
    """
    user_id = payload.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
        
    trace_detail = TokenTracker.get_trace_timeline(trace_id=trace_id, user_id=user_id)
    if not trace_detail:
        raise HTTPException(status_code=404, detail="Token trace not found")
        
    return {"status": "success", "trace": trace_detail}
