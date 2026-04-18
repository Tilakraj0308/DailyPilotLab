"""Shared Gmail thread listing / normalization (REST routes + agent tools)."""

from __future__ import annotations

from typing import Any

from connectors.providers.gmail import gmail_api

GMAIL_DEFAULT_PRIORITY_Q = "in:inbox newer_than:14d"
GMAIL_PRIORITY_MAX_THREADS = 15

_HEADER_KEYS_UI = frozenset(
    {
        "from",
        "to",
        "cc",
        "bcc",
        "subject",
        "date",
        "message-id",
        "in-reply-to",
        "references",
    }
)


def _payload_headers_subset(payload: dict | None) -> dict[str, str]:
    if not payload or "headers" not in payload:
        return {}
    out: dict[str, str] = {}
    for h in payload["headers"]:
        name = (h.get("name") or "").strip()
        if not name:
            continue
        lk = name.lower()
        if lk in _HEADER_KEYS_UI:
            out[lk] = h.get("value") or ""
    return out


def _message_internal_date_ms(m: dict[str, Any]) -> int:
    raw = m.get("internalDate")
    if raw is None:
        return 0
    try:
        return int(str(raw).strip())
    except ValueError:
        return 0


def _representative_message(messages: list[Any]) -> dict[str, Any] | None:
    """Latest message in thread by Gmail internalDate (milliseconds since epoch)."""
    best: dict[str, Any] | None = None
    best_ts = -1
    for m in messages:
        if not isinstance(m, dict):
            continue
        ts = _message_internal_date_ms(m)
        if ts > best_ts:
            best_ts = ts
            best = m
    return best


def thread_summary_dict_from_api(raw: dict[str, Any]) -> dict[str, Any]:
    """Shape aligned with GmailThreadSummaryOut (dict form for tools / JSON)."""
    tid = str(raw.get("id") or "")
    snippet = raw.get("snippet")
    snip_str = str(snippet) if isinstance(snippet, str) else None
    messages = raw.get("messages") or []
    if not isinstance(messages, list) or not messages:
        return {
            "id": tid,
            "snippet": snip_str,
            "subject": None,
            "from_addr": None,
            "internal_date_ms": None,
            "label_ids": [],
        }
    m0 = _representative_message(messages)
    if m0 is None:
        return {
            "id": tid,
            "snippet": snip_str,
            "subject": None,
            "from_addr": None,
            "internal_date_ms": None,
            "label_ids": [],
        }
    headers: dict[str, str] = {}
    pl = m0.get("payload")
    if isinstance(pl, dict):
        for h in pl.get("headers") or []:
            if not isinstance(h, dict):
                continue
            lk = (h.get("name") or "").lower()
            headers[lk] = h.get("value") or ""
    internal = m0.get("internalDate")
    labels = m0.get("labelIds")
    label_list = list(labels) if isinstance(labels, list) else []
    return {
        "id": tid,
        "snippet": snip_str,
        "subject": headers.get("subject"),
        "from_addr": headers.get("from"),
        "internal_date_ms": str(internal) if internal is not None else None,
        "label_ids": [str(x) for x in label_list],
    }


def normalize_thread_detail_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Same shape as the GET /gmail/threads/{id} JSON body."""
    tid = str(raw.get("id") or "")
    out_messages: list[dict[str, Any]] = []
    for m in raw.get("messages") or []:
        if not isinstance(m, dict):
            continue
        pl = m.get("payload")
        pl_dict = pl if isinstance(pl, dict) else None
        out_messages.append(
            {
                "id": str(m.get("id") or ""),
                "snippet": m.get("snippet"),
                "internalDate": m.get("internalDate"),
                "labelIds": list(m.get("labelIds") or [])
                if isinstance(m.get("labelIds"), list)
                else [],
                "headers": _payload_headers_subset(pl_dict),
            }
        )
    return {
        "id": tid,
        "snippet": raw.get("snippet"),
        "historyId": raw.get("historyId"),
        "messages": out_messages,
    }


def _priority_sort_key(item: dict[str, Any]) -> tuple[int, int, int]:
    """
    Ascending sort key for priority view: unread first, IMPORTANT label next,
    then newer internalDate first (via negated ms).
    """
    labels = item.get("label_ids") or []
    if not isinstance(labels, list):
        labels = []
    unread_rank = 0 if "UNREAD" in labels else 1
    important_rank = 0 if "IMPORTANT" in labels else 1
    raw_ms = item.get("internal_date_ms")
    try:
        ms = int(str(raw_ms).strip()) if raw_ms is not None else 0
    except ValueError:
        ms = 0
    return (unread_rank, important_rank, -ms)


def fetch_priority_threads(
    *,
    access_token: str,
    max_results: int,
    q: str,
) -> dict[str, Any]:
    """
    List inbox messages, preserve-order dedupe thread IDs, hydrate up to
    GMAIL_PRIORITY_MAX_THREADS (same behavior as GET /gmail/priority).
    """
    listed = gmail_api.list_inbox_messages(
        access_token=access_token,
        max_results=max_results,
        q=q,
    )
    msgs = listed.get("messages") or []
    if not isinstance(msgs, list):
        msgs = []

    thread_ids: list[str] = []
    seen: set[str] = set()
    for m in msgs:
        if not isinstance(m, dict):
            continue
        th = m.get("threadId")
        if not th or not isinstance(th, str):
            continue
        if th not in seen:
            seen.add(th)
            thread_ids.append(th)
    thread_ids = thread_ids[:GMAIL_PRIORITY_MAX_THREADS]

    items: list[dict[str, Any]] = []
    for thid in thread_ids:
        raw = gmail_api.get_thread(
            access_token=access_token,
            thread_id=thid,
            message_format="metadata",
        )
        if isinstance(raw, dict):
            items.append(thread_summary_dict_from_api(raw))

    items.sort(key=_priority_sort_key)

    return {"query": q, "items": items}
