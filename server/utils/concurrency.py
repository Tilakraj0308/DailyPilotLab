"""
Process-wide concurrency limits for high-load endpoints (backpressure).
"""
from __future__ import annotations

import asyncio
import os

from fastapi import HTTPException


def _chat_stream_max_concurrent() -> int:
    raw = os.getenv("CHAT_STREAM_MAX_CONCURRENT", "64")
    try:
        n = int(raw)
    except ValueError:
        return 64
    return max(1, min(n, 10_000))


def _chat_acquire_timeout_sec() -> float:
    try:
        return float(os.getenv("CHAT_STREAM_ACQUIRE_TIMEOUT_SEC", "30"))
    except ValueError:
        return 30.0


_chat_stream_semaphore: asyncio.Semaphore | None = None


def get_chat_stream_semaphore() -> asyncio.Semaphore:
    global _chat_stream_semaphore
    if _chat_stream_semaphore is None:
        _chat_stream_semaphore = asyncio.Semaphore(_chat_stream_max_concurrent())
    return _chat_stream_semaphore


class ChatStreamCapacityError(Exception):
    """Raised when chat stream slots are exhausted (translate to 503)."""


async def acquire_chat_stream_slot() -> None:
    sem = get_chat_stream_semaphore()
    try:
        await asyncio.wait_for(sem.acquire(), timeout=_chat_acquire_timeout_sec())
    except asyncio.TimeoutError as e:
        raise ChatStreamCapacityError(
            "Chat stream capacity reached; retry shortly."
        ) from e


def release_chat_stream_slot() -> None:
    sem = get_chat_stream_semaphore()
    try:
        sem.release()
    except ValueError:
        pass


def http_exception_for_chat_capacity(exc: ChatStreamCapacityError) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))
