"""Gmail — Google OAuth connector configuration."""

import os

from connectors.base_connector import GoogleOAuthConnector


def _normalize_redirect_uri(raw: str) -> str:
    u = raw.strip()
    if len(u) >= 2 and ((u[0] == u[-1] == '"') or (u[0] == u[-1] == "'")):
        u = u[1:-1].strip()
    return u.rstrip("/")


class GmailConnector(GoogleOAuthConnector):
    provider_key = "gmail"

    default_scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def _redirect_uri(self) -> str:
        explicit = _normalize_redirect_uri(os.getenv("GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI", ""))
        if explicit:
            return explicit

        cal = _normalize_redirect_uri(os.getenv("GOOGLE_CONNECTOR_REDIRECT_URI", ""))
        if cal and "google_calendar" in cal:
            return cal.replace("google_calendar", "gmail", 1)

        raise RuntimeError(
            "Set GOOGLE_GMAIL_CONNECTOR_REDIRECT_URI "
            "(e.g. http://127.0.0.1:8000/connectors/gmail/callback) "
            "or set GOOGLE_CONNECTOR_REDIRECT_URI with …/google_calendar/… so Gmail URL can be derived."
        )
