from __future__ import annotations

from collections.abc import Callable
from typing import Any

from utils.background_jobs.handlers.chat_summary_handler import run_chat_summary_job
from utils.background_jobs.models import JobType

HandlerFn = Callable[[dict[str, Any]], dict]


def get_job_handler(job_type: str) -> HandlerFn:
    if job_type == JobType.chat_summary.value:
        return run_chat_summary_job
    raise ValueError(f"Unknown job type: {job_type!r}")
