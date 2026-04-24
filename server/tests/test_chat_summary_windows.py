from __future__ import annotations

from utils.agent_chat_manager import (
    compute_closed_windows,
    mark_summary_retryable,
    process_post_assistant_message,
    resolve_summary_cycle,
)


def test_window_index_after_10_exchanges() -> None:
    assert compute_closed_windows(total_messages=20, exchange_size=2, window_exchanges=10) == [
        0
    ]


def test_no_window_before_boundary() -> None:
    assert compute_closed_windows(total_messages=18, exchange_size=2, window_exchanges=10) == []


def test_resolve_summary_cycle_from_env(monkeypatch) -> None:
    monkeypatch.setenv("summary_cycle", "3")
    assert resolve_summary_cycle() == 3

    monkeypatch.setenv("summary_cycle", "0")
    assert resolve_summary_cycle() == 10

    monkeypatch.setenv("summary_cycle", "invalid")
    assert resolve_summary_cycle() == 10


def test_process_post_assistant_message_enqueues_all_missing_closed_windows(
    monkeypatch,
) -> None:
    ensured_windows: list[int] = []

    def fake_load_agent_history(*, session_id: str, user_id: str, agent_id: str) -> list[dict]:
        assert session_id == "session-1"
        assert user_id == "user-1"
        assert agent_id == "agent-1"
        # 60 messages => closed windows [0, 1, 2]
        return [{} for _ in range(60)]

    def fake_ensure_summary_row(
        *,
        user_id: str,
        agent_id: str,
        session_id: str,
        window_index: int,
    ) -> dict:
        ensured_windows.append(window_index)
        return {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "window_index": window_index,
        }

    monkeypatch.setattr(
        "utils.agent_chat_manager.load_agent_history",
        fake_load_agent_history,
    )
    monkeypatch.setattr(
        "utils.agent_chat_manager.ensure_summary_row",
        fake_ensure_summary_row,
    )
    monkeypatch.setattr(
        "utils.agent_chat_manager.get_existing_summary_window_indexes",
        lambda **_: [0],
    )

    process_post_assistant_message(
        user_id="user-1",
        agent_id="agent-1",
        session_id="session-1",
    )

    assert ensured_windows == [1, 2]


def test_process_post_assistant_message_skips_when_no_closed_window(monkeypatch) -> None:
    ensured_windows: list[int] = []

    def fake_load_agent_history(*, session_id: str, user_id: str, agent_id: str) -> list[dict]:
        assert session_id == "session-2"
        assert user_id == "user-2"
        assert agent_id == "agent-2"
        return [{} for _ in range(18)]

    def fake_ensure_summary_row(
        *,
        user_id: str,
        agent_id: str,
        session_id: str,
        window_index: int,
    ) -> dict:
        ensured_windows.append(window_index)
        return {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "window_index": window_index,
        }

    monkeypatch.setattr(
        "utils.agent_chat_manager.load_agent_history",
        fake_load_agent_history,
    )
    monkeypatch.setattr(
        "utils.agent_chat_manager.ensure_summary_row",
        fake_ensure_summary_row,
    )
    monkeypatch.setattr(
        "utils.agent_chat_manager.get_existing_summary_window_indexes",
        lambda **_: None,
    )

    process_post_assistant_message(
        user_id="user-2",
        agent_id="agent-2",
        session_id="session-2",
    )

    assert ensured_windows == []


def test_process_post_assistant_message_repeated_non_boundary_no_enqueue_churn(
    monkeypatch,
) -> None:
    ensured_windows: list[int] = []

    def fake_load_agent_history(*, session_id: str, user_id: str, agent_id: str) -> list[dict]:
        assert session_id == "session-3"
        assert user_id == "user-3"
        assert agent_id == "agent-3"
        # 21 messages => latest closed window remains 0 (non-boundary progress)
        return [{} for _ in range(21)]

    def fake_ensure_summary_row(
        *,
        user_id: str,
        agent_id: str,
        session_id: str,
        window_index: int,
    ) -> dict:
        ensured_windows.append(window_index)
        return {
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "window_index": window_index,
        }

    monkeypatch.setattr(
        "utils.agent_chat_manager.load_agent_history",
        fake_load_agent_history,
    )
    monkeypatch.setattr(
        "utils.agent_chat_manager.ensure_summary_row",
        fake_ensure_summary_row,
    )
    monkeypatch.setattr(
        "utils.agent_chat_manager.get_existing_summary_window_indexes",
        lambda **_: [0],
    )

    process_post_assistant_message(
        user_id="user-3",
        agent_id="agent-3",
        session_id="session-3",
    )

    assert ensured_windows == []


def test_mark_summary_retryable_updates_status_and_retry_count(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_update_summary_status(
        *,
        summary_id: str,
        status: str,
        increment_retry: bool = False,
    ) -> dict:
        call = {
            "summary_id": summary_id,
            "status": status,
            "increment_retry": increment_retry,
        }
        calls.append(call)
        return call

    monkeypatch.setattr(
        "utils.agent_chat_manager.update_summary_status",
        fake_update_summary_status,
    )

    mark_summary_retryable(summary_id="summary-1")

    assert calls == [
        {
            "summary_id": "summary-1",
            "status": "pending_retry",
            "increment_retry": True,
        }
    ]
