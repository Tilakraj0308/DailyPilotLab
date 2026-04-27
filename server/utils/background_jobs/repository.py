from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg2.extras import Json

from db.dbConnection import get_dict_cursor
from utils.background_jobs.models import JobType

logger = logging.getLogger(__name__)


def enqueue_chat_summary_job(
    *,
    payload: dict[str, Any],
    idempotency_key: str,
    max_attempts: int,
) -> str | None:
    """
    Insert a pending job. Returns job id if inserted, None if idempotency key already exists.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.background_jobs (
                job_type, payload, status, run_at, max_attempts, idempotency_key
            )
            VALUES (%s, %s, 'pending', now(), %s, %s)
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING id::text
            """,
            (JobType.chat_summary.value, Json(payload), max_attempts, idempotency_key),
        )
        row = cur.fetchone()
        if not row:
            logger.info(
                "background_jobs enqueue skip duplicate idempotency_key=%s", idempotency_key
            )
            return None
        jid = str(row["id"])
        logger.info(
            "background_jobs enqueued id=%s type=%s idempotency_key=%s",
            jid,
            JobType.chat_summary.value,
            idempotency_key,
        )
        return jid


def claim_next_job(*, lease_seconds: int) -> dict[str, Any] | None:
    """
    Atomically claim one runnable job (pending, retry_scheduled, or stale in_progress).
    Does not increment attempt_count; failures increment in mark_job_failure.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            WITH next_job AS (
                SELECT id
                FROM public.background_jobs
                WHERE (
                        status IN ('pending', 'retry_scheduled')
                        OR (
                            status = 'in_progress'
                            AND (lease_until IS NULL OR lease_until < now())
                        )
                    )
                  AND run_at <= now()
                ORDER BY priority ASC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE public.background_jobs AS j
            SET
                status = 'in_progress',
                lease_until = now() + (%s::bigint * interval '1 second'),
                updated_at = now()
            FROM next_job
            WHERE j.id = next_job.id
            RETURNING
                j.id::text AS id,
                j.job_type,
                j.payload,
                j.status,
                j.priority,
                j.run_at,
                j.attempt_count,
                j.max_attempts,
                j.lease_until,
                j.idempotency_key,
                j.last_error,
                j.result,
                j.created_at,
                j.updated_at
            """,
            (lease_seconds,),
        )
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        logger.info(
            "background_jobs claimed id=%s type=%s idempotency_key=%s attempt_count=%s max_attempts=%s",
            d.get("id"),
            d.get("job_type"),
            d.get("idempotency_key"),
            d.get("attempt_count"),
            d.get("max_attempts"),
        )
        return d


def mark_job_done(*, job_id: str, result: dict[str, Any] | None = None) -> None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.background_jobs
            SET
                status = 'done',
                result = %s,
                lease_until = NULL,
                last_error = NULL,
                updated_at = now()
            WHERE id = %s
            """,
            (
                Json(result) if isinstance(result, dict) else result,
                job_id,
            ),
        )
    logger.info("background_jobs done id=%s", job_id)


def _compute_backoff_seconds(attempt_after_failure: int) -> float:
    """Exponential backoff with jitter; caps at 5 minutes."""
    base = min(2 ** min(attempt_after_failure, 8), 300)
    jitter = random.uniform(0, min(3.0, base * 0.2))
    return base + jitter


def mark_job_failure(
    *,
    job_id: str,
    error_message: str,
) -> str:
    """
    Increment failure count. If under max_attempts, schedule retry; else mark failed_terminal.
    Returns the new job status.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT attempt_count, max_attempts
            FROM public.background_jobs
            WHERE id = %s
            FOR UPDATE
            """,
            (job_id,),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("background job missing")
        new_attempts = int(row["attempt_count"]) + 1
        max_a = int(row["max_attempts"])
        if new_attempts >= max_a:
            cur.execute(
                """
                UPDATE public.background_jobs
                SET
                    status = 'failed_terminal',
                    attempt_count = %s,
                    lease_until = NULL,
                    last_error = %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (new_attempts, error_message, job_id),
            )
            logger.warning(
                "background_jobs failed_terminal id=%s attempts=%s error=%s",
                job_id,
                new_attempts,
                error_message[:200] if error_message else "",
            )
            return "failed_terminal"
        nxt = datetime.now(UTC) + timedelta(seconds=_compute_backoff_seconds(new_attempts))
        cur.execute(
            """
            UPDATE public.background_jobs
            SET
                status = 'retry_scheduled',
                attempt_count = %s,
                run_at = %s,
                lease_until = NULL,
                last_error = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (new_attempts, nxt, error_message, job_id),
        )
        logger.info(
            "background_jobs retry_scheduled id=%s attempt_count=%s run_at=%s",
            job_id,
            new_attempts,
            nxt.isoformat(),
        )
        return "retry_scheduled"


def count_active_jobs() -> int:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT count(*)::int AS c
            FROM public.background_jobs
            WHERE status IN ('pending', 'retry_scheduled', 'in_progress')
            """
        )
        row = cur.fetchone()
        return int(row["c"]) if row else 0


def get_queue_debug_snapshot() -> dict[str, Any]:
    """Lightweight status for logs / internal diagnostics."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT status, count(*)::int AS c
            FROM public.background_jobs
            GROUP BY status
            """
        )
        rows = cur.fetchall()
    return {str(r["status"]): r["c"] for r in rows}
