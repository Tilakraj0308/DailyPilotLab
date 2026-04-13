from fastapi import FastAPI, Response, UploadFile, File, Depends, Query
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel
import json
import asyncio
import time
from fastapi.middleware.cors import CORSMiddleware
from utils.idea_manager import get_ideas, create_idea, create_ideas, update_idea, delete_idea, delete_ideas, delete_all_ideas, raw_to_refined_ideas
from models.ideas import IdeaCreateInput, IdeaOut, IdeaUpdateInput, IdeaDeleteInput
from models.users import GoogleAuthRequest, AuthResponse, UserOut
from models.connectors import ConnectorStatus, ConnectorListResponse, CalendarEventsResponse
from utils.helpers import assign_idea_to_topic, semantic_search_memories, update_traits
from services.auth_service import get_or_create_user
from utils.auth_middleware import get_current_user, get_current_user_id
from utils.crypto import verify_oauth_state
from services.connectors_service import (
    build_google_auth_url,
    exchange_code_for_tokens,
    fetch_google_identity,
    upsert_connector,
    get_connector_status,
    get_all_connectors,
    revoke_connector,
    fetch_calendar_events,
    ConnectorRevokedException,
    ConnectorRateLimitException,
    ConnectorUnavailableException,
)
from typing import List, Optional
from dotenv import load_dotenv
from utils.topic_manager import update_topic_recency
from services.chat_service import transcribe_audio, stream_chat
from services.chat_db import get_or_create_session, save_message, load_history

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Health Check Endpoint ──────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Quick health check - useful for debugging connection issues"""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "message": "Backend is running and accessible"
    }
    
@app.get("/ping")
def ping():
    """Ultra-lightweight ping for mobile network tests"""
    return {"pong": True}


# ─── Audio Transcription (Whisper) ──────────────────────────────────────────

@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """
    Transcribe audio file using OpenAI Whisper API.
    
    Accepts: WAV, MP3, FLAC, OGG, OPUS, and other formats
    Returns: Transcribed text
    """
    try:
        print("INSIDE THE FUNTION")
        # Read the audio file
        audio_bytes = await file.read()
        
        if not audio_bytes:
            return {"error": "Audio file is empty"}, 400
        
        # Convert to base64 for the transcribe_audio function
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        print("GOING TO TRANSCRIBE")
        # Transcribe using OpenAI Whisper API
        transcript = await transcribe_audio(audio_b64)
        
        return {
            "success": True,
            "text": transcript,
            "original_filename": file.filename,
            "timestamp": time.time()
        }
        
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        return {"error": str(e), "success": False}, 500


# ─── Authentication ─────────────────────────────────────────────────────────

# @app.post("/auth/google", response_model=AuthResponse)
# def google_auth(payload: GoogleAuthRequest):
#     """
#     Authenticate via Google OAuth.
#     The client sends the Google ID token obtained from Google Sign-In.
#     """
#     # 1. Verify the Google ID token
#     google_info = verify_google_token(payload.id_token)

#     # 2. Get or create user in our DB
#     user = get_or_create_user(
#         google_id=google_info["sub"],
#         email=google_info.get("email", ""),
#         display_name=google_info.get("name"),
#         avatar_url=google_info.get("picture"),
#     )

#     # 3. Issue our own JWT
#     access_token = create_access_token(user["id"])

#     # 4. Return JWT + user info
#     return AuthResponse(
#         access_token=access_token,
#         user=UserOut(**user),
#     )

@app.get("/auth/profile")
def sync_profile(payload: dict = Depends(get_current_user)):
    """
    Syncs the Supabase user profile into the custom public.users table.
    Expects a valid Supabase JWT in the Authorization header.
    """
    user_metadata = payload.get("user_metadata", {})
    email = payload.get("email", "")
    auth_id = payload.get("sub", "")
    name = user_metadata.get("full_name") or user_metadata.get("name")
    avatar_url = user_metadata.get("avatar_url")
    
    user = get_or_create_user(auth_id, email, name, avatar_url)
    return {"status": "success", "user": user}

# ─── Ideas ───────────────────────────────────────────────────────────────────
    
@app.get("/ideas", response_model=List[IdeaOut])
def getIdeas(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    return get_ideas(user_id)

@app.post("/ideas")
def createIdea(idea: IdeaCreateInput, response: Response, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    creation_response = create_idea(idea, user_id)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

@app.post("/ideas/bulk")
def createIdeas(ideas: List[IdeaCreateInput], response: Response, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    creation_response = create_ideas(ideas, user_id)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

@app.post("/ideas/update")
def updateIdea(idea: IdeaUpdateInput, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    return update_idea(idea, user_id)

@app.post("/ideas/delete")
def deleteIdea(idea: IdeaDeleteInput, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    return delete_idea(idea, user_id)

@app.post("/ideas/delete/bulk")
def deleteIdeas(idea_ids: List[int], payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    return delete_ideas(idea_ids, user_id)

@app.post("/ideas/delete/all")
def deleteAllIdeas(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    return delete_all_ideas(user_id)

@app.get("/topics/assign")
def assignTopics(response: Response, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    creation_response = assign_idea_to_topic(user_id)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

@app.get("/semantic-search")
def semanticSearch(query: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    return semantic_search_memories(query, user_id=user_id)

@app.get("/refine-ideas")
def refineIdeas(response: Response, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    refine_response = raw_to_refined_ideas(user_id=user_id)
    response.status_code = refine_response['status']
    return {'message': refine_response['message']}

@app.get("/update-topic-recency")
def updateTopicRecency(response: Response, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    update_response = update_topic_recency(user_id)
    response.status_code = update_response['status']
    return {'message': update_response['message']}

@app.get("/update-traits")  
def updateTraits(response: Response, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    update_response = update_traits(user_id)
    response.status_code = update_response['status']
    return {'message': update_response['message']}


# ─── Chat ────────────────────────────────────────────────────────────────────

class ChatStreamRequest(BaseModel):
    session_id: str
    content: str

@app.post("/chat/stream")
async def chat_stream(req: ChatStreamRequest, payload: dict = Depends(get_current_user)):
    session_id = req.session_id
    user_text = req.content
    user_id = payload.get("sub", "")

    await asyncio.to_thread(get_or_create_session, session_id, user_id)
    await asyncio.to_thread(save_message, session_id, "user", user_text)

    history_rows = await asyncio.to_thread(load_history, session_id)
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows]

    async def event_stream():
        full_response = ""
        async for token in stream_chat(history):
            full_response += token
            yield f'data: {json.dumps({"type": "token", "content": token})}\n\n'
        
        await asyncio.to_thread(save_message, session_id, "assistant", full_response)
        yield f'data: {json.dumps({"type": "done", "content": ""})}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─── Connectors ─────────────────────────────────────────────────────────────

@app.get("/connectors", response_model=ConnectorListResponse)
def list_connectors(user_id: int = Depends(get_current_user_id)):
    """List all connectors for the authenticated user."""
    connectors = get_all_connectors(user_id)
    return ConnectorListResponse(
        connectors=[
            ConnectorStatus(
                provider=c["provider"],
                connected=c["connected"],
                provider_account_email=c.get("provider_account_email"),
                scopes=c.get("scopes", []),
                expires_at=c.get("expires_at"),
                connected_at=c.get("connected_at"),
                last_sync_at=c.get("last_sync_at"),
                needs_reconnect=c["needs_reconnect"],
            )
            for c in connectors
        ]
    )


@app.get("/connectors/google/calendar/start")
def connector_google_calendar_start(
    user_id: int = Depends(get_current_user_id),
    deep_link: Optional[str] = Query(None)
):
    """
    Generate the Google OAuth consent URL for Calendar access.
    The URL contains a signed state parameter binding the session to this user.
    """
    auth_url = build_google_auth_url(user_id, deep_link)
    return {"auth_url": auth_url}


@app.get("/connectors/google/calendar/callback")
def connector_google_calendar_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """
    OAuth callback from Google. This endpoint is NOT JWT-protected.
    Authentication is via the HMAC-signed state parameter.

    On success: redirects to the app via deep link.
    On failure: redirects to the app with error info.
    """
    base_redirect = "dailypilot://connectors/callback"

    # Handle user cancellation / consent denied
    if error:
        print(f"OAuth error: {error}")
        return RedirectResponse(
            url=f"{base_redirect}?status=error&reason=cancelled",
            status_code=302,
        )

    if not code or not state:
        return RedirectResponse(
            url=f"{base_redirect}?status=error&reason=missing_params",
            status_code=302,
        )

    # Validate signed state → extract user_id & deep link
    try:
        user_id, deep_link = verify_oauth_state(state)
        # Use provided deep link or fallback to default
        if deep_link:
            base_redirect = deep_link
    except ValueError as e:
        print(f"State validation failed: {e}")
        return RedirectResponse(
            url=f"{base_redirect}?status=error&reason=invalid_state",
            status_code=302,
        )

    # Exchange code for tokens
    try:
        tokens = exchange_code_for_tokens(code)
    except ValueError as e:
        print(f"Token exchange failed: {e}")
        return RedirectResponse(
            url=f"{base_redirect}?status=error&reason=exchange_failed",
            status_code=302,
        )

    # Fetch Google identity
    try:
        identity = fetch_google_identity(tokens["access_token"])
    except ValueError as e:
        print(f"Identity fetch failed: {e}")
        return RedirectResponse(
            url=f"{base_redirect}?status=error&reason=identity_failed",
            status_code=302,
        )

    # Persist encrypted tokens
    try:
        upsert_connector(
            user_id=user_id,
            provider="google_calendar",
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens.get("expires_in", 3600),
            scopes=tokens.get("scope", ""),
            provider_account_id=identity["id"],
            provider_account_email=identity["email"],
        )
    except Exception as e:
        print(f"Connector upsert failed: {e}")
        return RedirectResponse(
            url=f"{base_redirect}?status=error&reason=save_failed",
            status_code=302,
        )

    return RedirectResponse(
        url=f"{base_redirect}?status=success",
        status_code=302,
    )


@app.get("/connectors/google/calendar/status", response_model=ConnectorStatus)
def connector_google_calendar_status(user_id: int = Depends(get_current_user_id)):
    """Get the connection status of Google Calendar for the authenticated user."""
    status_data = get_connector_status(user_id, "google_calendar")
    if not status_data:
        return ConnectorStatus(
            provider="google_calendar",
            connected=False,
            needs_reconnect=False,
        )
    return ConnectorStatus(
        provider=status_data["provider"],
        connected=status_data["connected"],
        provider_account_email=status_data.get("provider_account_email"),
        scopes=status_data.get("scopes", []),
        expires_at=status_data.get("expires_at"),
        connected_at=status_data.get("connected_at"),
        last_sync_at=status_data.get("last_sync_at"),
        needs_reconnect=status_data["needs_reconnect"],
    )


@app.post("/connectors/google/calendar/disconnect")
def connector_google_calendar_disconnect(
    user_id: int = Depends(get_current_user_id),
):
    """Disconnect Google Calendar — revokes locally and clears stored tokens."""
    revoked = revoke_connector(user_id, "google_calendar")
    if not revoked:
        return {"status": "not_connected", "message": "No active connection found"}
    return {"status": "disconnected", "message": "Google Calendar disconnected"}


@app.get("/connectors/google/calendar/events", response_model=CalendarEventsResponse)
def connector_google_calendar_events(
    user_id: int = Depends(get_current_user_id),
    time_min: Optional[str] = Query(None, description="ISO datetime lower bound"),
    time_max: Optional[str] = Query(None, description="ISO datetime upper bound"),
):
    """
    Fetch upcoming calendar events from Google Calendar.
    Handles token refresh, revocation detection, and rate limits.
    """
    try:
        events = fetch_calendar_events(
            user_id=user_id,
            time_min=time_min,
            time_max=time_max,
        )
        from datetime import datetime, timezone
        return CalendarEventsResponse(
            events=events,
            synced_at=datetime.now(timezone.utc).isoformat(),
        )
    except ConnectorRevokedException as e:
        return Response(
            content=json.dumps({"error": str(e), "needs_reconnect": True}),
            status_code=401,
            media_type="application/json",
        )
    except ConnectorRateLimitException as e:
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=429,
            media_type="application/json",
        )
    except ConnectorUnavailableException as e:
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=502,
            media_type="application/json",
        )
