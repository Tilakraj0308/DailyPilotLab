from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from services.agent_chat_db import update_chat_summary_failed
from utils.background_jobs.config import SummaryWorkerConfig, load_summary_worker_config
from utils.background_jobs.models import JobType
from utils.background_jobs.registry import get_job_handler
from utils.background_jobs.repository import (
    claim_next_job,
    get_queue_debug_snapshot,
    mark_job_done,
    mark_job_failure,
)

logger = logging.getLogger(__name__)

_heartbeat: dict[str, Any] = {
    "running": False,
    "last_poll_at": None,
    "last_error": None,
    "config": None,
    "last_claim_duration_ms": None,
    "last_job_duration_ms": None,
    "jobs_completed": 0,
    "jobs_failed": 0,
    "last_queue_snapshot": None,
}


def get_worker_heartbeat() -> dict[str, Any]:
    return dict(_heartbeat)


class SummaryBackgroundWorker:
    """
    Polls the generic background_jobs table and runs chat_summary handlers.
    Intended to be started as an asyncio task from FastAPI lifespan.
    """

    def __init__(self, config: SummaryWorkerConfig | None = None) -> None:
        self._config = config or load_summary_worker_config()
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def config(self) -> SummaryWorkerConfig:
        return self._config

    def start(self) -> None:
        if not self._config.enabled:
            logger.info("SummaryBackgroundWorker disabled (SUMMARY_WORKER_ENABLED=false)")
            return
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name="summary-background-worker")
        _heartbeat["running"] = True
        _heartbeat["config"] = {
            "poll_interval_ms": self._config.poll_interval_ms,
            "concurrency": self._config.concurrency,
            "batch_size": self._config.batch_size,
        }
        logger.info("SummaryBackgroundWorker started")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=30.0)
            except asyncio.TimeoutError:
                self._task.cancel()
        _heartbeat["running"] = False
        self._task = None
        logger.info("SummaryBackgroundWorker stopped")

    async def _run_loop(self) -> None:
        sem = asyncio.Semaphore(self._config.concurrency)
        poll_sec = self._config.poll_interval_ms / 1000.0

        poll_count = 0
        while not self._stop.is_set():
            _heartbeat["last_poll_at"] = datetime.now(UTC).isoformat()
            batch: list[asyncio.Task[None]] = []
            try:
                for _ in range(self._config.batch_size):
                    if self._stop.is_set():
                        break
                    t_claim = time.perf_counter()
                    job = await asyncio.to_thread(
                        claim_next_job,
                        lease_seconds=self._config.lease_seconds,
                    )
                    _heartbeat["last_claim_duration_ms"] = round(
                        (time.perf_counter() - t_claim) * 1000.0, 2
                    )
                    if not job:
                        break
                    batch.append(asyncio.create_task(self._process_with_sem(sem, job)))

                if batch:
                    poll_count = 0
                    await asyncio.gather(*batch)
                else:
                    poll_count += 1
                    if poll_count % 20 == 0:
                        try:
                            snap = await asyncio.to_thread(get_queue_debug_snapshot)
                            _heartbeat["last_queue_snapshot"] = snap
                            logger.info(
                                "background_jobs queue_snapshot poll=%s snapshot=%s",
                                poll_count,
                                snap,
                            )
                        except Exception as snap_e:
                            logger.debug("queue snapshot failed: %s", snap_e)
                    try:
                        await asyncio.wait_for(self._stop.wait(), timeout=poll_sec)
                    except asyncio.TimeoutError:
                        pass
            except Exception as e:
                _heartbeat["last_error"] = str(e)
                logger.exception("SummaryBackgroundWorker loop error: %s", e)
                await asyncio.sleep(1.0)

    async def _process_with_sem(self, sem: asyncio.Semaphore, job: dict) -> None:
        async with sem:
            if self._stop.is_set():
                return
            await asyncio.to_thread(self._execute_job, job)

    def _execute_job(self, job: dict) -> None:
        job_id = str(job["id"])
        job_type = str(job["job_type"])
        t0 = time.perf_counter()
        try:
            logger.info(
                "SummaryBackgroundWorker execute_start id=%s type=%s", job_id, job_type
            )
            handler = get_job_handler(job_type)
            result = handler(job)
            mark_job_done(job_id=job_id, result=result)
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            _heartbeat["last_job_duration_ms"] = elapsed_ms
            _heartbeat["jobs_completed"] = int(_heartbeat.get("jobs_completed") or 0) + 1
            logger.info(
                "SummaryBackgroundWorker execute_ok id=%s duration_ms=%s", job_id, elapsed_ms
            )
        except Exception as e:
            _heartbeat["last_error"] = str(e)
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            _heartbeat["last_job_duration_ms"] = elapsed_ms
            _heartbeat["jobs_failed"] = int(_heartbeat.get("jobs_failed") or 0) + 1
            logger.warning(
                "Job %s type=%s failed after %sms: %s",
                job_id,
                job_type,
                elapsed_ms,
                e,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            status = mark_job_failure(job_id=job_id, error_message=str(e))
            if status == "failed_terminal" and job_type == JobType.chat_summary.value:
                self._mark_chat_summary_domain_failed(job, str(e))

    def _mark_chat_summary_domain_failed(self, job: dict, err: str) -> None:
        try:
            raw = job.get("payload")
            if isinstance(raw, str):
                raw = json.loads(raw)
            summary_row_id = str(raw.get("summary_row_id", ""))
            if not summary_row_id:
                return
            update_chat_summary_failed(summary_id=summary_row_id, error_message=err)
        except Exception as e2:
            logger.error("Failed to mark chat_summary domain row terminal: %s", e2)
