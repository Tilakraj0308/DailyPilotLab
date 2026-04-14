from fastapi import FastAPI, Response, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel
import json
import asyncio
import time
from fastapi.middleware.cors import CORSMiddleware
from utils.idea_manager import get_ideas, create_idea, create_ideas, update_idea, delete_idea, delete_ideas, delete_all_ideas, raw_to_refined_ideas
from models.ideas import IdeaCreateInput, IdeaOut, IdeaUpdateInput, IdeaDeleteInput
from models.users import GoogleAuthRequest, AuthResponse, UserOut
from utils.helpers import assign_idea_to_topic, semantic_search_memories, update_traits
from services.auth_service import get_or_create_user
from utils.auth_middleware import get_current_user
from typing import List 
from dotenv import load_dotenv
from utils.topic_manager import update_topic_recency
from services.chat_service import transcribe_audio, stream_chat
from services.chat_db import get_or_create_session, save_message, load_history
from models.connectors import (
    ConnectorDisconnectResponse,
    ConnectorListResponse,
    ConnectorStartRequest,
    ConnectorStartResponse,
    ConnectorStatusItem,
)
from services import connector_service as connector_svc
from services.google_calendar_connector_service import (
    build_start_authorization_url,
    complete_oauth_callback,
    oauth_error_callback,
    revoke_and_disconnect,
)

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

# ─── Connectors (OAuth — separate client from Supabase login) ─────────────────

@app.get("/connectors", response_model=ConnectorListResponse)
def list_connectors(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    rows = connector_svc.list_connectors_status(user_id)
    items = [
        ConnectorStatusItem(
            provider_key=r["provider_key"],
            display_name=r["display_name"],
            status=r["status"],
            scopes=list(r["scopes"] or []),
            connected_at=r["connected_at"],
            provider_email=r.get("provider_email"),
            error_message=r.get("error_message"),
        )
        for r in rows
    ]
    return ConnectorListResponse(connectors=items)


@app.post("/connectors/{provider}/start", response_model=ConnectorStartResponse)
def connector_start(
    provider: str,
    body: ConnectorStartRequest,
    payload: dict = Depends(get_current_user),
):
    user_id = payload.get("sub", "")
    if provider != "google_calendar":
        raise HTTPException(status_code=404, detail="Unknown connector provider")
    try:
        url, state = build_start_authorization_url(user_id, body.return_to)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return ConnectorStartResponse(authorization_url=url, state=state)


@app.get("/connectors/{provider}/callback")
def connector_oauth_callback(provider: str, request: Request):
    """Public OAuth redirect target (Google). Validates state and exchanges the code."""
    if provider != "google_calendar":
        raise HTTPException(status_code=404, detail="Unknown connector provider")
    q = request.query_params
    err = q.get("error")
    state = q.get("state")
    code = q.get("code")
    if err:
        url = oauth_error_callback(state, err)
        return RedirectResponse(url=url, status_code=302)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    try:
        redirect_url, _, _ = complete_oauth_callback(code, state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return RedirectResponse(url=redirect_url, status_code=302)


@app.post("/connectors/{provider}/disconnect", response_model=ConnectorDisconnectResponse)
def connector_disconnect(provider: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    if provider != "google_calendar":
        raise HTTPException(status_code=404, detail="Unknown connector provider")
    try:
        revoke_and_disconnect(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return ConnectorDisconnectResponse(ok=True, provider_key=provider)

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

