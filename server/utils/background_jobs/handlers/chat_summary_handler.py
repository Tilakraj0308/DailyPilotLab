from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import yaml
from openai import OpenAI

from services.agent_chat_db import load_agent_messages_in_turn_range, update_chat_summary_done
from utils.background_jobs.models import (
    ChatSummaryJobPayload,
    WindowSummaryLLMResult,
)

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAPI"))
    return _client


def _load_prompt_template() -> dict[str, str]:
    base = Path(__file__).resolve().parent.parent.parent.parent / "config" / "prompts"
    path = base / "chat_window_summary.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_chat_summary_job(job: dict) -> dict:
    """
    Synchronous handler: loads window, calls OpenAI, persists chat_summaries.
    Returns a small result dict for background_jobs.result.
    Raises on any failure (worker applies retries / terminal + domain failure row).
    """
    logger.info("chat_summary_handler job_id=%s", job.get("id"))
    raw = job["payload"]
    if isinstance(raw, str):
        raw = json.loads(raw)
    payload = ChatSummaryJobPayload.model_validate(raw)

    rows = load_agent_messages_in_turn_range(
        session_id=payload.session_id,
        user_id=payload.user_id,
        agent_id=payload.agent_id,
        start_turn=payload.window_start_turn,
        end_turn=payload.window_end_turn,
    )
    if not rows:
        raise ValueError(
            f"No messages for window {payload.window_index} "
            f"turns {payload.window_start_turn}-{payload.window_end_turn}"
        )

    messages_json = json.dumps(
        [{"role": r["role"], "content": r["content"]} for r in rows],
        ensure_ascii=False,
    )
    template = _load_prompt_template()
    system_msg = template["system"].strip()
    user_msg = template["user"].format(messages_json=messages_json)

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1200,
    )
    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("OpenAI returned empty content for summary")

    content = response.choices[0].message.content
    data = json.loads(content)
    parsed = WindowSummaryLLMResult.model_validate(
        {
            "summary_text": data.get("summary_text", ""),
            "extracted_payload": data.get("extracted_payload")
            or data.get("extracted")
            or {},
        }
    )

    update_chat_summary_done(
        summary_id=payload.summary_row_id,
        summary_text=parsed.summary_text,
        extracted_payload=parsed.extracted_payload,
    )
    out = {
        "summary_row_id": payload.summary_row_id,
        "window_index": payload.window_index,
    }
    logger.info(
        "chat_summary job done user=%s session=%s window=%s",
        payload.user_id,
        payload.session_id,
        payload.window_index,
    )
    return out
