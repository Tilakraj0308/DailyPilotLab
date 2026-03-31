import os
import base64
import tempfile
from openai import AsyncOpenAI
from typing import AsyncGenerator

client = AsyncOpenAI(api_key=os.getenv("OPENAPI"))

async def transcribe_audio(audio_b64: str) -> str:
    """Decode base64 WAV -> call Whisper -> return transcript."""
    audio_bytes = base64.b64decode(audio_b64)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

async def stream_chat(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Stream GPT-4o-mini tokens."""
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=True,
        max_tokens=1024,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
