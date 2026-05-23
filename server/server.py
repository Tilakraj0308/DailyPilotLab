from fastapi import FastAPI, Response, UploadFile, File, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from pydantic import BaseModel
import json
import asyncio
import time
from fastapi.middleware.cors import CORSMiddleware
from utils.idea_manager import get_ideas, create_idea, create_ideas, update_idea, delete_idea, delete_ideas, delete_all_ideas, raw_to_refined_ideas
from models.ideas import IdeaCreateInput, IdeaOut, IdeaUpdateInput, IdeaDeleteInput
# from models.users import GoogleAuthRequest, AuthResponse, UserOut
from utils.helpers import assign_idea_to_topic, semantic_search_memories, update_traits
from services.auth_service import get_or_create_user
from utils.auth_middleware import get_current_user
from typing import List 
from dotenv import load_dotenv
from utils.topic_manager import update_topic_recency
from services.chat_service import transcribe_audio, stream_chat
# from services.chat_db import ChatSessionAccessError, get_or_create_session, save_message, load_history, get_user_sessions
from services.chat_db import save_message, load_history
# from models.chat import ChatSessionSummary
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
    session_id: str
    content: str

@app.post("/chat/stream")
async def chat_stream(req: ChatStreamRequest, payload: dict = Depends(get_current_user)):
    user_text = req.content
    user_id = payload.get("sub", "")

    # Save user message
    await asyncio.to_thread(save_message, user_id, "user", user_text)

    # Context Assembly: Working Memory
    history_rows = await asyncio.to_thread(load_history, user_id, limit=10, offset=0)
    # The history comes DESC from load_history, we need it ASC for streaming context
    history_rows = list(reversed(history_rows))
    
    # Context Assembly: System Persona, Long-Term Traits, Personal State, Short-Term Ideas
    from services.trait_service import TraitsService
    from utils.idea_manager import get_raw_ideas
    from services.ideas_service import IdeaService
    import os
    
    # Base instructions could be fetched from config, using a placeholder for now
    persona = "You are DailyPilot, an advanced personal companion and assistant."
    
    # Traits
    traits_data = ""
    try:
        ts = TraitsService()
        traits = ts.get_user_traits(user_id)
        if traits:
            traits_str = "\n".join([f"- {t['trait_text']} (Type: {t['trait_type']})" for t in traits])
            traits_data = f"User Traits:\n{traits_str}"
    except:
        pass
        
    # Personal State
    from services.user_service import get_personal_state
    personal_state_data = ""
    try:
        state_dict = get_personal_state(user_id)
        if state_dict:
            personal_state_data = f"Personal State:\n{json.dumps(state_dict)}"
    except:
        pass
            
    # Short-Term Memory (Active Ideas)
    active_ideas_data = ""
    try:
        active_ideas = get_raw_ideas(user_id)
        if active_ideas:
            ideas_str = "\n".join([f"- {i['content']}" for i in active_ideas])
            active_ideas_data = f"Recent Thoughts & Ideas:\n{ideas_str}"
    except:
        pass

    system_content = f"{persona}\n\n{traits_data}\n\n{personal_state_data}\n\n{active_ideas_data}".strip()

    history = [{"role": "system", "content": system_content}]
    history.extend([{"role": r["role"], "content": r["content"]} for r in history_rows])

    async def event_stream():
        full_response = ""
        async for token in stream_chat(history, user_id):
            full_response += token
            yield f'data: {json.dumps({"type": "token", "content": token})}\n\n'
        
        await asyncio.to_thread(save_message, user_id, "assistant", full_response)
        yield f'data: {json.dumps({"type": "done", "content": ""})}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")

import uuid

@app.get("/chat/history")
def get_chat_user_history(limit: int = 15, offset: int = 0, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    history_rows = load_history(user_id, limit=limit, offset=offset)
    # History rows are DESC (newest first). Let the frontend keep it DESC if used in Inverted FlatList.
    history = [{"id": str(uuid.uuid4()) if 'id' not in r else str(r['id']), "role": r["role"], "content": r["content"], "created_at": r.get('created_at')} for r in history_rows]
    return {"history": history}

