"""Google Calendar — connector OAuth configuration."""

import os
from connectors.base_connector import BaseConnector


class CalendarConnector(BaseConnector):
    provider_key = "google_calendar"
    default_scopes = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def _redirect_uri(self) -> str:
        uri = os.getenv("GOOGLE_CONNECTOR_REDIRECT_URI", "").strip()
        if not uri:
            raise RuntimeError("GOOGLE_CONNECTOR_REDIRECT_URI is required for Google Calendar connector")
        return uri
