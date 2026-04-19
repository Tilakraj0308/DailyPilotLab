from pydantic import BaseModel
from typing import Literal

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    type: Literal["text", "audio"]
    content: str | None = None        # for text messages
    audio_data: str | None = None     # base64-encoded WAV for audio
    session_id: str                   # UUID string from client
    history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    type: Literal["token", "transcription", "done", "error"]
    content: str

class ChatSessionSummary(BaseModel):
    id: str
    updated_at: str
    created_at: str
    title: str | None = None

