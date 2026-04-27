"""
Thread-based backpressure for sync FastAPI routes (e.g. connector HTTP handlers).
"""
from __future__ import annotations

import os
import threading
from collections.abc import Generator
from contextlib import contextmanager

from fastapi import HTTPException


def _connector_max_concurrent() -> int:
    try:
        n = int(os.getenv("CONNECTOR_HTTP_MAX_CONCURRENT", "128"))
    except ValueError:
        return 128
    return max(1, min(n, 10_000))


def _connector_acquire_timeout_sec() -> float:
    try:
        return float(os.getenv("CONNECTOR_HTTP_ACQUIRE_TIMEOUT_SEC", "60"))
    except ValueError:
        return 60.0


_connector_sem = threading.BoundedSemaphore(_connector_max_concurrent())


@contextmanager
def connector_request_slot() -> Generator[None, None, None]:
    ok = _connector_sem.acquire(timeout=_connector_acquire_timeout_sec())
    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Connector request capacity reached; retry shortly.",
        )
    try:
        yield
    finally:
        _connector_sem.release()


def connector_slot_dependency() -> Generator[None, None, None]:
    """FastAPI dependency: one connector slot for the duration of the request."""
    with connector_request_slot():
        yield
