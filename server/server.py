from fastapi import FastAPI, Response, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
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
from uuid import UUID
from dotenv import load_dotenv
from utils.topic_manager import update_topic_recency
from services.chat_service import transcribe_audio, stream_chat
from services.chat_db import ChatSessionAccessError, get_or_create_session, save_message, load_history, get_user_sessions
from services.agent_chat_db import (
    AgentSessionAccessError,
    ensure_default_agent,
)
from models.chat import ChatSessionSummary
from models.agent_chat import AgentChatStreamRequest
from utils.agent_chat_manager import stream_agent_chat
from connectors import router as connectors_router

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(connectors_router, prefix="/connectors", tags=["connectors"])

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
    session_id: UUID
    content: str

@app.post("/agent-chat/stream")
async def agent_chat_stream(
    req: AgentChatStreamRequest, payload: dict = Depends(get_current_user)
):
    user_id = payload.get("sub", "")
    try:
        return await stream_agent_chat(req=req, user_id=user_id)
    except AgentSessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@app.post("/agents/default/ensure")
def ensure_default_agent_endpoint(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    return ensure_default_agent(user_id)


@app.post("/chat/stream")
async def chat_stream(req: ChatStreamRequest, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    default_agent = await asyncio.to_thread(ensure_default_agent, user_id)
    wrapped = AgentChatStreamRequest(
        agent_id=str(default_agent["id"]),
        session_id=str(req.session_id),
        content=req.content,
    )
    try:
        return await stream_agent_chat(req=wrapped, user_id=user_id)
    except AgentSessionAccessError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

@app.get("/chat/sessions", response_model=List[ChatSessionSummary])
def get_chat_sessions(limit: int = 15, offset: int = 0, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    sessions = get_user_sessions(user_id, limit=limit, offset=offset)
    return [
        ChatSessionSummary(
            id=str(s["id"]),
            updated_at=str(s["updated_at"]),
            created_at=str(s["created_at"]),
            title=s["title"]
        ) for s in sessions
    ]

@app.get("/chat/sessions/{session_id}/history")
def get_chat_session_history(session_id: str, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    history_rows = load_history(session_id)
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows]
    return {"history": history}

