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
