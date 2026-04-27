from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int, *, min_value: int | None = 1) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        v = int(raw)
    except ValueError:
        return default
    if min_value is not None and v < min_value:
        return default
    return v


@dataclass(frozen=True, slots=True)
class SummaryWorkerConfig:
    """Runtime settings for the chat-summary background worker (from env)."""

    enabled: bool
    poll_interval_ms: int
    batch_size: int
    concurrency: int
    lease_seconds: int
    max_job_retries: int  # used as default max_attempts on new jobs; matches env naming


def load_summary_worker_config() -> SummaryWorkerConfig:
    return SummaryWorkerConfig(
        enabled=_env_bool("SUMMARY_WORKER_ENABLED", False),
        poll_interval_ms=_env_int("SUMMARY_WORKER_POLL_INTERVAL_MS", 1500, min_value=50),
        batch_size=_env_int("SUMMARY_WORKER_BATCH_SIZE", 5, min_value=1),
        concurrency=_env_int("SUMMARY_WORKER_CONCURRENCY", 3, min_value=1),
        lease_seconds=_env_int("SUMMARY_WORKER_LEASE_SECONDS", 45, min_value=5),
        max_job_retries=_env_int("SUMMARY_WORKER_MAX_RETRIES", 5, min_value=1),
    )
