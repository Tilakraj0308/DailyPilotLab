from __future__ import annotations

import base64
import importlib
from email import message_from_bytes
from unittest.mock import Mock

import pytest
import requests.exceptions
from fastapi import FastAPI
from fastapi.testclient import TestClient

import utils.openAi as openai_utils

from connectors.models import GmailAiDraftSuggestionOut
from connectors.router import router
from utils.auth_middleware import get_current_user

# `connectors/__init__.py` binds `connectors.router` to the APIRouter instance;
# patch the actual module object via importlib.
router_module = importlib.import_module("connectors.router")


class FakeGmailConnector:
    def ensure_access_token(self, user_id: str) -> str:
        assert user_id == "test-user"
        return "fake-access-token"


@pytest.fixture
def gmail_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setitem(
        router_module.PROVIDER_MAP,
        "gmail",
        lambda: FakeGmailConnector(),
    )
    app = FastAPI()
    app.include_router(router, prefix="/connectors")
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user",
        "email": "test@example.com",
    }
    return TestClient(app)


def test_gmail_priority_hydrates_threads(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_list(*, access_token: str, max_results, q: str):
        assert access_token == "fake-access-token"
        assert q == "in:inbox newer_than:14d"
        assert max_results == 30
        return {
            "messages": [
                {"id": "m1", "threadId": "t-unread-imp"},
                {"id": "m2", "threadId": "t-read"},
                {"id": "m3", "threadId": "t-unread-plain"},
            ]
        }

    def fake_get_thread(*, access_token: str, thread_id: str, message_format: str = "metadata"):
        assert access_token == "fake-access-token"
        assert message_format == "metadata"
        calls.append(("get", thread_id))
        if thread_id == "t-read":
            # Latest-by-internalDate is second message; labels INBOX only (read).
            return {
                "id": thread_id,
                "snippet": f"snip-{thread_id}",
                "messages": [
                    {
                        "id": "m-old",
                        "snippet": "old",
                        "internalDate": "1000",
                        "labelIds": ["INBOX"],
                        "payload": {
                            "headers": [
                                {"name": "Subject", "value": "Stale subject"},
                                {"name": "From", "value": "old@example.com"},
                            ]
                        },
                    },
                    {
                        "id": f"msg-{thread_id}",
                        "snippet": "hello",
                        "internalDate": "9000",
                        "labelIds": ["INBOX"],
                        "payload": {
                            "headers": [
                                {"name": "Subject", "value": "Read thread"},
                                {"name": "From", "value": "alice@example.com"},
                            ]
                        },
                    },
                ],
            }
        if thread_id == "t-unread-imp":
            return {
                "id": thread_id,
                "snippet": f"snip-{thread_id}",
                "messages": [
                    {
                        "id": f"msg-{thread_id}",
                        "snippet": "hello",
                        "internalDate": "1000",
                        "labelIds": ["INBOX", "UNREAD", "IMPORTANT"],
                        "payload": {
                            "headers": [
                                {"name": "Subject", "value": "Important unread"},
                                {"name": "From", "value": "alice@example.com"},
                            ]
                        },
                    }
                ],
            }
        return {
            "id": thread_id,
            "snippet": f"snip-{thread_id}",
            "messages": [
                {
                    "id": f"msg-{thread_id}",
                    "snippet": "hello",
                    "internalDate": "5000",
                    "labelIds": ["INBOX", "UNREAD"],
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Plain unread"},
                            {"name": "From", "value": "alice@example.com"},
                        ]
                    },
                }
            ],
        }

    monkeypatch.setattr(router_module.gmail_api, "list_inbox_messages", fake_list)
    monkeypatch.setattr(router_module.gmail_api, "get_thread", fake_get_thread)

    r = gmail_client.get("/connectors/gmail/priority")
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "in:inbox newer_than:14d"
    assert len(data["items"]) == 3
    # Unread+IMPORTANT, then unread without IMPORTANT (newer internalDate does not outrank IMPORTANT),
    # then read. Summary uses latest message by internalDate.
    assert [x["id"] for x in data["items"]] == [
        "t-unread-imp",
        "t-unread-plain",
        "t-read",
    ]
    assert data["items"][0]["subject"] == "Important unread"
    assert data["items"][1]["subject"] == "Plain unread"
    assert data["items"][2]["subject"] == "Read thread"
    assert calls == [
        ("get", "t-unread-imp"),
        ("get", "t-read"),
        ("get", "t-unread-plain"),
    ]


def test_gmail_priority_max_results_passed_through(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    def fake_list(*, access_token: str, max_results, q: str):
        captured["max_results"] = max_results
        return {"messages": []}

    monkeypatch.setattr(router_module.gmail_api, "list_inbox_messages", fake_list)
    monkeypatch.setattr(
        router_module.gmail_api,
        "get_thread",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("no threads")),
    )

    r = gmail_client.get("/connectors/gmail/priority", params={"max_results": 5})
    assert r.status_code == 200
    assert captured["max_results"] == 5


def test_gmail_ai_suggest_reply_uses_thread_and_openai(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    def fake_get_thread(*, access_token: str, thread_id: str, message_format: str = "metadata"):
        captured["thread_id"] = thread_id
        assert message_format == "metadata"
        return {
            "id": thread_id,
            "snippet": "snip",
            "messages": [
                {
                    "id": "m1",
                    "snippet": "hi",
                    "internalDate": "1",
                    "labelIds": ["INBOX"],
                    "payload": {"headers": [{"name": "From", "value": "bob@example.com"}]},
                }
            ],
        }

    def fake_completion(system_prompt: str, user_prompt: str, response_format=None, model: str = "gpt-3.5-turbo"):
        captured["system"] = system_prompt
        captured["user"] = user_prompt
        assert response_format is GmailAiDraftSuggestionOut
        assert "draft" in system_prompt.lower()
        return GmailAiDraftSuggestionOut(subject="Re: Hello", body_text="Thanks for your note.")

    monkeypatch.setattr(router_module.gmail_api, "get_thread", fake_get_thread)
    monkeypatch.setattr(openai_utils.openai_client, "get_chat_completion", fake_completion)

    r = gmail_client.post("/connectors/gmail/ai/suggest-reply", json={"thread_id": "thr-ai"})
    assert r.status_code == 200
    assert r.json() == {"subject": "Re: Hello", "body_text": "Thanks for your note."}
    assert captured["thread_id"] == "thr-ai"
    assert "thr-ai" in captured["user"]


def test_gmail_ai_suggest_reply_rejects_empty_body(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        router_module.gmail_api,
        "get_thread",
        lambda **kwargs: {"id": "t", "messages": []},
    )

    def fake_completion(**kwargs):
        return GmailAiDraftSuggestionOut(subject=None, body_text="   ")

    monkeypatch.setattr(openai_utils.openai_client, "get_chat_completion", fake_completion)

    r = gmail_client.post("/connectors/gmail/ai/suggest-reply", json={"thread_id": "t"})
    assert r.status_code == 502


def test_gmail_thread_detail_normalized(gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_thread(*, access_token: str, thread_id: str, message_format: str = "metadata"):
        assert thread_id == "thr99"
        return {
            "id": "thr99",
            "snippet": "thread snip",
            "historyId": "h1",
            "messages": [
                {
                    "id": "m-a",
                    "snippet": "a",
                    "internalDate": "1",
                    "labelIds": ["INBOX"],
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "x@y.com"},
                            {"name": "To", "value": "z@y.com"},
                            {"name": "Subject", "value": "Hi"},
                            {"name": "Cc", "value": "c@y.com"},
                        ]
                    },
                }
            ],
        }

    monkeypatch.setattr(router_module.gmail_api, "get_thread", fake_get_thread)

    r = gmail_client.get("/connectors/gmail/threads/thr99")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "thr99"
    assert body["snippet"] == "thread snip"
    assert body["historyId"] == "h1"
    assert len(body["messages"]) == 1
    m = body["messages"][0]
    assert m["id"] == "m-a"
    assert m["headers"]["from"] == "x@y.com"
    assert m["headers"]["to"] == "z@y.com"
    assert m["headers"]["subject"] == "Hi"
    assert m["headers"]["cc"] == "c@y.com"


def test_gmail_create_draft_encodes_rfc822_and_thread(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    received: dict = {}

    def fake_create(*, access_token: str, body: dict):
        received["body"] = body
        return {
            "id": "draft-1",
            "message": {"id": "msg-new", "threadId": "th-reply"},
        }

    monkeypatch.setattr(router_module.gmail_api, "create_draft", fake_create)

    r = gmail_client.post(
        "/connectors/gmail/drafts",
        json={
            "thread_id": "th-reply",
            "to": ["bob@example.com"],
            "subject": "Re: hi",
            "body_text": "Body line",
        },
    )
    assert r.status_code == 200
    assert r.json() == {
        "draft_id": "draft-1",
        "message_id": "msg-new",
        "thread_id": "th-reply",
    }
    raw = received["body"]["message"]["raw"]
    padded = raw + "=" * ((4 - len(raw) % 4) % 4)
    decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    msg = message_from_bytes(decoded)
    assert msg["to"] == "bob@example.com"
    assert msg["subject"] == "Re: hi"
    assert msg.get_payload() == "Body line\n"
    assert received["body"]["message"]["threadId"] == "th-reply"


def test_gmail_send_draft(gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_send(*, access_token: str, draft_id: str):
        assert draft_id == "draft-xyz"
        return {"id": "sent-msg-id", "labelIds": ["SENT"]}

    monkeypatch.setattr(router_module.gmail_api, "send_draft", fake_send)

    r = gmail_client.post("/connectors/gmail/drafts/draft-xyz/send")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "id": "sent-msg-id"}


def test_gmail_create_draft_logs_history(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    logged: list[dict] = []

    def capture_log(**kwargs):
        logged.append(kwargs)

    monkeypatch.setattr(router_module.history, "log_tool_call", capture_log)

    def fake_create(*, access_token: str, body: dict):
        return {"id": "draft-1", "message": {"id": "msg-new", "threadId": "th-reply"}}

    monkeypatch.setattr(router_module.gmail_api, "create_draft", fake_create)

    r = gmail_client.post(
        "/connectors/gmail/drafts",
        json={
            "thread_id": "th-reply",
            "to": ["bob@example.com"],
            "subject": "Re: hi",
            "body_text": "Body line",
        },
    )
    assert r.status_code == 200
    assert len(logged) == 1
    assert logged[0]["user_id"] == "test-user"
    assert logged[0]["provider_key"] == "gmail"
    assert logged[0]["tool_name"] == "gmail_ui_create_draft"
    assert logged[0]["crud_type"] == "create"
    assert logged[0]["triggered_by"] == "user"
    assert logged[0]["status"] == "success"
    assert logged[0]["params"] == {
        "thread_id": "th-reply",
        "draft_id": "draft-1",
        "message_id": "msg-new",
    }
    assert logged[0]["result_summary"] == {
        "draft_id": "draft-1",
        "thread_id": "th-reply",
        "message_id": "msg-new",
    }


def test_gmail_send_draft_logs_history(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    logged: list[dict] = []

    def capture_log(**kwargs):
        logged.append(kwargs)

    monkeypatch.setattr(router_module.history, "log_tool_call", capture_log)

    def fake_send(*, access_token: str, draft_id: str):
        return {"id": "sent-msg-id", "threadId": "th-1", "labelIds": ["SENT"]}

    monkeypatch.setattr(router_module.gmail_api, "send_draft", fake_send)

    r = gmail_client.post("/connectors/gmail/drafts/draft-xyz/send")
    assert r.status_code == 200
    assert len(logged) == 1
    assert logged[0]["tool_name"] == "gmail_ui_send_draft"
    assert logged[0]["crud_type"] == "update"
    assert logged[0]["params"] == {"draft_id": "draft-xyz", "thread_id": "th-1"}
    assert logged[0]["result_summary"] == {"message_id": "sent-msg-id", "thread_id": "th-1"}


def test_gmail_thread_detail_maps_404(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get_thread(**kwargs):
        resp = Mock()
        resp.status_code = 404
        raise requests.exceptions.HTTPError(response=resp)

    monkeypatch.setattr(router_module.gmail_api, "get_thread", fake_get_thread)

    r = gmail_client.get("/connectors/gmail/threads/missing")
    assert r.status_code == 404
    assert r.json()["detail"] == "Gmail resource not found"


def test_gmail_create_draft_maps_404(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_create(**kwargs):
        resp = Mock()
        resp.status_code = 404
        raise requests.exceptions.HTTPError(response=resp)

    monkeypatch.setattr(router_module.gmail_api, "create_draft", fake_create)

    r = gmail_client.post(
        "/connectors/gmail/drafts",
        json={"to": ["a@b.com"], "subject": "s", "body_text": "x"},
    )
    assert r.status_code == 404


def test_gmail_send_draft_maps_404(
    gmail_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_send(**kwargs):
        resp = Mock()
        resp.status_code = 404
        raise requests.exceptions.HTTPError(response=resp)

    monkeypatch.setattr(router_module.gmail_api, "send_draft", fake_send)

    r = gmail_client.post("/connectors/gmail/drafts/bad-draft/send")
    assert r.status_code == 404
