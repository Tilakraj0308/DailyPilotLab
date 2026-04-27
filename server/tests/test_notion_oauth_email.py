"""Notion OAuth token payload → person email (strict app-email policy)."""

from connectors.providers.notion.connector import notion_owner_person_email_from_token_payload


def test_notion_owner_person_email_from_user_person_payload():
    payload = {
        "access_token": "x",
        "owner": {
            "type": "user",
            "user": {
                "object": "user",
                "id": "u1",
                "type": "person",
                "person": {"email": "Alice@Example.com"},
            },
        },
    }
    assert notion_owner_person_email_from_token_payload(payload) == "Alice@Example.com"


def test_notion_owner_person_email_workspace_owner_returns_none():
    payload = {
        "owner": {"type": "workspace", "workspace": True},
    }
    assert notion_owner_person_email_from_token_payload(payload) is None


def test_notion_owner_person_email_missing_owner():
    assert notion_owner_person_email_from_token_payload({}) is None
