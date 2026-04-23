from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import server as server_module
import utils.agent_chat_manager as manager_module
from services.agent_chat_db import AgentSessionAccessError
from utils.auth_middleware import get_current_user


@pytest.fixture
def client():
    server_module.app.dependency_overrides[get_current_user] = lambda: {"sub": "route-test-user"}
    with TestClient(server_module.app) as test_client:
        yield test_client
    server_module.app.dependency_overrides.clear()


def test_agent_chat_stream_requires_agent_id(client: TestClient):
    response = client.post(
        "/agent-chat/stream",
        json={"session_id": str(uuid4()), "content": "hello"},
    )
    assert response.status_code == 422


def test_agent_chat_stream_sends_tokens_and_done_event(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    calls: dict[str, list | tuple | None] = {
        "save": [],
        "process": None,
    }

    def fake_get_or_create_agent_session(session_id: str, user_id: str, agent_id: str) -> str:
        return session_id

    def fake_save_agent_message(*, session_id: str, user_id: str, agent_id: str, role: str, content: str) -> dict:
        calls["save"].append((session_id, user_id, agent_id, role, content))
        return {"role": role, "content": content}

    def fake_load_agent_history(*, session_id: str, user_id: str, agent_id: str) -> list[dict]:
        return [{"role": "user", "content": "hello"}]

    async def fake_stream_chat(history: list[dict], user_id: str):
        assert history == [{"role": "user", "content": "hello"}]
        assert user_id == "route-test-user"
        for token in ("A", "B"):
            yield token

    def fake_process_post_assistant_message(*, user_id: str, agent_id: str, session_id: str) -> None:
        calls["process"] = (user_id, agent_id, session_id)

    monkeypatch.setattr(
        manager_module, "get_or_create_agent_session", fake_get_or_create_agent_session
    )
    monkeypatch.setattr(manager_module, "save_agent_message", fake_save_agent_message)
    monkeypatch.setattr(manager_module, "load_agent_history", fake_load_agent_history)
    monkeypatch.setattr(manager_module, "stream_chat", fake_stream_chat)
    monkeypatch.setattr(
        manager_module,
        "process_post_assistant_message",
        fake_process_post_assistant_message,
    )

    agent_id = str(uuid4())
    session_id = str(uuid4())
    response = client.post(
        "/agent-chat/stream",
        json={"agent_id": agent_id, "session_id": session_id, "content": "hello"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '{"type": "token", "content": "A"}' in response.text
    assert '{"type": "token", "content": "B"}' in response.text
    assert '{"type": "done", "content": ""}' in response.text
    assert calls["save"] == [
        (session_id, "route-test-user", agent_id, "user", "hello"),
        (session_id, "route-test-user", agent_id, "assistant", "AB"),
    ]
    assert calls["process"] == ("route-test-user", agent_id, session_id)


def test_agent_chat_stream_returns_403_on_session_access_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def fake_get_or_create_agent_session(session_id: str, user_id: str, agent_id: str) -> str:
        raise AgentSessionAccessError("Session id is not valid for this user+agent pair")

    monkeypatch.setattr(
        manager_module, "get_or_create_agent_session", fake_get_or_create_agent_session
    )

    response = client.post(
        "/agent-chat/stream",
        json={"agent_id": str(uuid4()), "session_id": str(uuid4()), "content": "hello"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Session id is not valid for this user+agent pair"


def test_chat_stream_wraps_to_default_agent(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    default_agent_id = str(uuid4())

    def fake_ensure_default_agent(user_id: str) -> dict:
        assert user_id == "route-test-user"
        return {"id": default_agent_id}

    async def fake_agent_chat_stream(*, req, user_id: str):
        assert str(req.agent_id) == default_agent_id
        assert str(req.session_id) == "00000000-0000-0000-0000-000000000555"
        assert req.content == "legacy-route"
        assert user_id == "route-test-user"
        return {"ok": True, "agent_id": str(req.agent_id), "session_id": str(req.session_id)}

    monkeypatch.setattr(server_module, "ensure_default_agent", fake_ensure_default_agent)
    monkeypatch.setattr(server_module, "stream_agent_chat", fake_agent_chat_stream)

    response = client.post(
        "/chat/stream",
        json={
            "session_id": "00000000-0000-0000-0000-000000000555",
            "content": "legacy-route",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "agent_id": default_agent_id,
        "session_id": "00000000-0000-0000-0000-000000000555",
    }


def test_chat_stream_rejects_invalid_legacy_session_id(client: TestClient):
    response = client.post(
        "/chat/stream",
        json={
            "session_id": "not-a-uuid",
            "content": "legacy-route",
        },
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert isinstance(errors, list)
    assert any(err.get("loc") == ["body", "session_id"] for err in errors)
