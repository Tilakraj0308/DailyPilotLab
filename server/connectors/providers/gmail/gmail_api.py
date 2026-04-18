from __future__ import annotations

import logging
import urllib.parse
from typing import Any

import requests

logger = logging.getLogger(__name__)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _clamp_max_results(max_results: int | str) -> int:
    """Return maxResults in 1..50; non-coercible values use 30."""
    default = 30
    try:
        n = int(max_results)
    except (TypeError, ValueError):
        return default
    return max(1, min(50, n))


def list_inbox_messages(*, access_token: str, max_results: int | str, q: str) -> dict[str, Any]:
    params = {
        "maxResults": str(_clamp_max_results(max_results)),
        "labelIds": "INBOX",
        "q": q,
    }
    url = f"{GMAIL_API_BASE}/users/me/messages?{urllib.parse.urlencode(params)}"
    r = requests.get(url, headers=_auth_headers(access_token), timeout=30)
    if r.status_code != 200:
        logger.warning("gmail list messages failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def get_thread(
    *, access_token: str, thread_id: str, message_format: str = "metadata"
) -> dict[str, Any]:
    tid = urllib.parse.quote(thread_id, safe="")
    params = urllib.parse.urlencode({"format": message_format})
    url = f"{GMAIL_API_BASE}/users/me/threads/{tid}?{params}"
    r = requests.get(url, headers=_auth_headers(access_token), timeout=45)
    if r.status_code != 200:
        logger.warning("gmail get thread failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def create_draft(*, access_token: str, body: dict[str, Any]) -> dict[str, Any]:
    url = f"{GMAIL_API_BASE}/users/me/drafts"
    r = requests.post(url, headers=_auth_headers(access_token), json=body, timeout=45)
    if r.status_code != 200:
        logger.warning("gmail create draft failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def send_draft(*, access_token: str, draft_id: str) -> dict[str, Any]:
    did = urllib.parse.quote(draft_id, safe="")
    url = f"{GMAIL_API_BASE}/users/me/drafts/send"
    r = requests.post(url, headers=_auth_headers(access_token), json={"id": did}, timeout=45)
    if r.status_code != 200:
        logger.warning("gmail send draft failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()
