from __future__ import annotations

from typing import Any

import pytest

from connectors.providers.gmail.tools import create as gmail_create
from connectors.providers.gmail.tools import read as gmail_read
from connectors.providers.gmail.tools import update as gmail_update


class FakeGmailConnector:
    def ensure_access_token(self, user_id: str) -> str:
        assert user_id == "u1"
        return "fake-token"


def test_gmail_list_priority_threads_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_list(*, access_token: str, max_results, q: str):
        assert access_token == "fake-token"
        assert q == "in:inbox newer_than:14d"
        assert max_results == 30
        return {
            "messages": [
                {"id": "m1", "threadId": "t1"},
                {"id": "m2", "threadId": "t1"},
            ]
        }

    def fake_get_thread(*, access_token: str, thread_id: str, message_format: str = "metadata"):
        assert access_token == "fake-token"
        assert message_format == "metadata"
        calls.append((thread_id, message_format))
        return {
            "id": thread_id,
            "snippet": f"snip-{thread_id}",
            "messages": [
                {
                    "id": f"msg-{thread_id}",
                    "snippet": "hello",
                    "internalDate": "1700000000000",
                    "labelIds": ["INBOX", "UNREAD"],
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": f"Sub {thread_id}"},
                            {"name": "From", "value": "alice@example.com"},
                        ]
                    },
                }
            ],
        }

    import connectors.providers.gmail.gmail_api as gmail_api_mod

    monkeypatch.setattr(gmail_api_mod, "list_inbox_messages", fake_list)
    monkeypatch.setattr(gmail_api_mod, "get_thread", fake_get_thread)

    conn = FakeGmailConnector()
    out = gmail_read.execute(conn, "u1", "gmail_list_priority_threads", {})
    assert out["query"] == "in:inbox newer_than:14d"
    assert len(out["items"]) == 1
    assert out["items"][0]["id"] == "t1"
    assert out["items"][0]["subject"] == "Sub t1"
    assert calls == [("t1", "metadata")]


def test_gmail_list_priority_threads_custom_q(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_list(*, access_token: str, max_results, q: str):
        captured["q"] = q
        captured["max_results"] = max_results
        return {"messages": []}

    import connectors.providers.gmail.gmail_api as gmail_api_mod

    monkeypatch.setattr(gmail_api_mod, "list_inbox_messages", fake_list)
    monkeypatch.setattr(
        gmail_api_mod,
        "get_thread",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("no threads")),
    )

    conn = FakeGmailConnector()
    gmail_read.execute(
        conn,
        "u1",
        "gmail_list_priority_threads",
        {"q": "is:unread", "max_results": 5},
    )
    assert captured["q"] == "is:unread"
    assert captured["max_results"] == 5


def test_gmail_get_thread_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_thread(*, access_token: str, thread_id: str, message_format: str = "metadata"):
        assert access_token == "fake-token"
        assert thread_id == "thr1"
        assert message_format == "full"
        return {
            "id": "thr1",
            "snippet": "s",
            "historyId": "h",
            "messages": [
                {
                    "id": "m1",
                    "snippet": "a",
                    "internalDate": "1",
                    "labelIds": ["INBOX"],
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Hi"},
                        ]
                    },
                }
            ],
        }

    import connectors.providers.gmail.gmail_api as gmail_api_mod

    monkeypatch.setattr(gmail_api_mod, "get_thread", fake_get_thread)

    conn = FakeGmailConnector()
    body = gmail_read.execute(
        conn,
        "u1",
        "gmail_get_thread",
        {"thread_id": "thr1", "message_format": "full"},
    )
    assert body["id"] == "thr1"
    assert body["messages"][0]["headers"]["subject"] == "Hi"


def test_gmail_create_draft_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    received: dict[str, Any] = {}

    def fake_create(*, access_token: str, body: dict):
        assert access_token == "fake-token"
        received["body"] = body
        return {"id": "d1", "message": {"id": "m1", "threadId": "th1"}}

    import connectors.providers.gmail.gmail_api as gmail_api_mod

    monkeypatch.setattr(gmail_api_mod, "create_draft", fake_create)

    conn = FakeGmailConnector()
    out = gmail_create.execute(
        conn,
        "u1",
        "gmail_create_draft",
        {
            "subject": "S",
            "body_text": "Hello",
            "to": ["a@b.com"],
            "thread_id": "th1",
        },
    )
    assert out == {"draft_id": "d1", "message_id": "m1", "thread_id": "th1"}
    assert received["body"]["message"]["threadId"] == "th1"
    assert "raw" in received["body"]["message"]


def test_gmail_send_draft_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_send(*, access_token: str, draft_id: str):
        assert access_token == "fake-token"
        assert draft_id == "draft-9"
        return {"id": "sent-1", "labelIds": ["SENT"]}

    import connectors.providers.gmail.gmail_api as gmail_api_mod

    monkeypatch.setattr(gmail_api_mod, "send_draft", fake_send)

    conn = FakeGmailConnector()
    out = gmail_update.execute(conn, "u1", "gmail_send_draft", {"draft_id": "draft-9"})
    assert out == {"ok": True, "id": "sent-1"}
