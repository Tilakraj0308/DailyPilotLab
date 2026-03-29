from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, UploadFile, File, Depends
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
        # Read the audio file
        audio_bytes = await file.read()
        
        if not audio_bytes:
            return {"error": "Audio file is empty"}, 400
        
        # Convert to base64 for the transcribe_audio function
        import base64
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        
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
    google_id = payload.get("sub", "")
    name = user_metadata.get("full_name") or user_metadata.get("name")
    avatar_url = user_metadata.get("avatar_url")
    
    user = get_or_create_user(google_id, email, name, avatar_url)
    return {"status": "success", "user": user}

# ─── Ideas ───────────────────────────────────────────────────────────────────
    
@app.get("/ideas", response_model=List[IdeaOut])
# @app.get("/ideas")
def getIdeas():
    return get_ideas()

@app.post("/ideas")
def createIdea(idea: IdeaCreateInput, response: Response):
    creation_response = create_idea(idea)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

@app.post("/ideas/bulk")
def createIdeas(ideas: List[IdeaCreateInput], response: Response):
    creation_response = create_ideas(ideas)
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

@app.post("/ideas/update")
def updateIdea(idea: IdeaUpdateInput):
    return update_idea(idea)

# @app.post("/ideas/update/bulk")
# def updateIdeas(ideas: List[IdeaUpdateInput]):
#     return update_ideas(ideas)

@app.post("/ideas/delete")
def deleteIdea(idea: IdeaDeleteInput):
    return delete_idea(idea)

@app.post("/ideas/delete/bulk")
def deleteIdeas(idea_ids: List[int]):
    return delete_ideas(idea_ids)

@app.post("/ideas/delete/all")
def deleteAllIdeas():
    return delete_all_ideas()

@app.get("/topics/assign")
def assignTopics(response: Response):
    creation_response = assign_idea_to_topic()
    response.status_code = creation_response['status']
    return {'message': creation_response['message']}

@app.get("/semantic-search")
def semanticSearch(query: str):
    return semantic_search_memories(query)

@app.get("/refine-ideas")
def refineIdeas(response: Response):
    refine_response = raw_to_refined_ideas()
    response.status_code = refine_response['status']
    return {'message': refine_response['message']}

@app.get("/update-topic-recency")
def updateTopicRecency(response: Response):
    update_response = update_topic_recency()
    response.status_code = update_response['status']
    return {'message': update_response['message']}

@app.get("/update-traits")  
def updateTraits(response: Response):
    update_response = update_traits()
    response.status_code = update_response['status']
    return {'message': update_response['message']}


# ─── Chat ────────────────────────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    session_id = None
    last_ping_time = time.time()
    ping_interval = 30  # Send ping every 30 seconds to keep connection alive
    
    try:
        while True:
            try:
                # Use receive_text with timeout to allow periodic pings
                # Wait for message with 20 second timeout
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=20.0)
                req = json.loads(raw)
                session_id = req["session_id"]
                last_ping_time = time.time()  # Reset ping timer on message

                await asyncio.to_thread(get_or_create_session, session_id)

                # Resolve user text
                if req.get("type") == "audio" and req.get("audio_data"):
                    user_text = await transcribe_audio(req["audio_data"])
                    await websocket.send_json({
                        "type": "transcription", "content": user_text
                    })
                else:
                    user_text = req.get("content", "")

                # Persist user message
                await asyncio.to_thread(save_message, session_id, "user", user_text)

                # Load full history from DB for context
                history_rows = await asyncio.to_thread(load_history, session_id)
                history = [{"role": r["role"], "content": r["content"]} for r in history_rows]

                # Stream GPT response
                full_response = ""
                async for token in stream_chat(history):
                    full_response += token
                    await websocket.send_json({"type": "token", "content": token})

                # Persist assistant message
                await asyncio.to_thread(save_message, session_id, "assistant", full_response)
                await websocket.send_json({"type": "done", "content": ""})
                
            except asyncio.TimeoutError:
                # No message received in timeout period - send keepalive ping
                current_time = time.time()
                if current_time - last_ping_time >= ping_interval:
                    try:
                        await websocket.send_json({"type": "ping", "timestamp": current_time})
                        last_ping_time = current_time
                        print(f"Sent keepalive ping for session {session_id if session_id else 'unknown'}")
                    except Exception as ping_error:
                        print(f"Failed to send ping: {ping_error}")
                        break

    except WebSocketDisconnect:
        print(f"Chat websocket disconnected for session {session_id if session_id else 'unknown'}")
    except Exception as e:
        print(f"Chat error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": f"Server error: {str(e)}"})
        except:
            pass  # Connection already closed

