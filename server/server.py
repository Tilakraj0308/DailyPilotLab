from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, UploadFile, File, Depends
import json
import asyncio
import time
import os
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
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from deepgram import DeepgramClient
from deepgram.core.events import EventType
import threading
import queue
from services.chat_service import stream_chat, transcribe_audio
from services.chat_db import get_or_create_session, save_message, load_history

class ChatRequest(BaseModel):
    session_id: str
    content: str

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

@app.post("/api/chat")
async def chat_http(req: ChatRequest):
    session_id = req.session_id
    user_text = req.content

    await asyncio.to_thread(get_or_create_session, session_id)
    await asyncio.to_thread(save_message, session_id, "user", user_text)

    history_rows = await asyncio.to_thread(load_history, session_id)
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows]

    async def sse_generator():
        full_response = ""
        try:
            async for token in stream_chat(history):
                full_response += token
                # Yield standard SSE token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            await asyncio.to_thread(save_message, session_id, "assistant", full_response)
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        except Exception as e:
            print(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    })

@app.websocket("/ws/transcribe")
async def transcribe_live_ws(websocket: WebSocket):
    await websocket.accept()
    audio_queue = queue.Queue()
    is_active = threading.Event()
    is_active.set()
    loop = asyncio.get_running_loop()

    def deepgram_thread():
        try:
            client = DeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY", ""))
            
            with client.listen.v1.connect(
                model="nova-3",
                language="en",
                smart_format="true",
                interim_results="false"
            ) as connection:
                
                def on_message(*args, **kwargs):
                    if not is_active.is_set():
                        return
                    result = kwargs.get('result') or (args[1] if len(args) > 1 else args[0])
                    channel = getattr(result, "channel", None)
                    if channel and hasattr(channel, "alternatives"):
                        transcript = channel.alternatives[0].transcript
                        is_final = getattr(result, "is_final", False)
                        if transcript:
                            asyncio.run_coroutine_threadsafe(
                                websocket.send_json({"text": transcript, "is_final": is_final}),
                                loop
                            )

                def on_error(*args, **kwargs):
                    error = kwargs.get('error') or (args[1] if len(args) > 1 else args[0])
                    print(f"Deepgram error: {error}")

                connection.on(EventType.MESSAGE, on_message)
                connection.on(EventType.ERROR, on_error)

                def consume_queue():
                    while is_active.is_set():
                        try:
                            chunk = audio_queue.get(timeout=0.1)
                            if chunk is None:
                                break
                            connection.send_media(chunk)
                        except queue.Empty:
                            continue
                    try:
                        connection.finish()
                    except Exception as e:
                        pass

                cq_thread = threading.Thread(target=consume_queue, daemon=True)
                cq_thread.start()

                connection.start_listening()
        except Exception as e:
            print(f"Deepgram thread error: {e}")

    dg_thread = threading.Thread(target=deepgram_thread, daemon=True)
    dg_thread.start()

    try:
        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break
            if "text" in data:
                import base64
                payload = json.loads(data["text"])
                if payload.get("type") == "audio" and dict.get(payload, "data"):
                    chunk = base64.b64decode(payload["data"])
                    audio_queue.put(chunk)
            elif "bytes" in data:
                audio_queue.put(data["bytes"])
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WS Transcribe Error: {e}")
    finally:
        is_active.clear()
        audio_queue.put(None)

