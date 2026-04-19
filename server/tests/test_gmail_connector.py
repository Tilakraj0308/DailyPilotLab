from unittest.mock import Mock, patch

from connectors.providers import PROVIDER_MAP
from connectors.providers.gmail import gmail_api


def test_gmail_provider_registered():
    assert "gmail" in PROVIDER_MAP
    connector_cls = PROVIDER_MAP["gmail"]
    inst = connector_cls()
    assert getattr(inst, "provider_key", None) == "gmail"


@patch("connectors.providers.gmail.gmail_api.requests.get")
def test_list_inbox_messages_builds_expected_url(mock_get: Mock):
    mock_get.return_value = Mock(status_code=200, json=lambda: {"messages": []})

    gmail_api.list_inbox_messages(access_token="token", max_results=10, q="in:inbox")

    args, kwargs = mock_get.call_args
    assert args[0].startswith("https://gmail.googleapis.com/gmail/v1/users/me/messages")
    assert "maxResults=10" in args[0]
    assert "q=" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer token"


@patch("connectors.providers.gmail.gmail_api.requests.get")
def test_list_inbox_messages_non_int_max_results_defaults(mock_get: Mock):
    mock_get.return_value = Mock(status_code=200, json=lambda: {"messages": []})

    gmail_api.list_inbox_messages(access_token="t", max_results="not-a-number", q="in:inbox")

    args, _kwargs = mock_get.call_args
    assert "maxResults=30" in args[0]


@patch("connectors.providers.gmail.gmail_api.requests.get")
def test_get_thread_builds_expected_url(mock_get: Mock):
    mock_get.return_value = Mock(status_code=200, json=lambda: {"id": "thr1"})

    gmail_api.get_thread(access_token="token", thread_id="abc+def", message_format="full")

    args, kwargs = mock_get.call_args
    assert args[0].startswith("https://gmail.googleapis.com/gmail/v1/users/me/threads/")
    assert "abc%2Bdef" in args[0]
    assert "format=full" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer token"


@patch("connectors.providers.gmail.gmail_api.requests.post")
def test_create_draft_posts_expected_request(mock_post: Mock):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"id": "draft1"})
    body = {"message": {"raw": "dGVzdA"}}

    gmail_api.create_draft(access_token="token", body=body)

    args, kwargs = mock_post.call_args
    assert args[0] == "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
    assert kwargs["json"] == body
    assert kwargs["headers"]["Authorization"] == "Bearer token"


@patch("connectors.providers.gmail.gmail_api.requests.post")
def test_send_draft_posts_expected_json(mock_post: Mock):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"id": "msg1"})

    gmail_api.send_draft(access_token="token", draft_id="r-abc")

    args, kwargs = mock_post.call_args
    assert args[0] == "https://gmail.googleapis.com/gmail/v1/users/me/drafts/send"
    assert kwargs["json"] == {"id": "r-abc"}
    assert kwargs["headers"]["Authorization"] == "Bearer token"
