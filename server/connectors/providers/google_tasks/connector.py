"""Google Tasks — connector OAuth configuration."""

import os
import logging
from connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)


def _normalize_redirect_uri(raw: str) -> str:
    u = raw.strip()
    if len(u) >= 2 and ((u[0] == u[-1] == '"') or (u[0] == u[-1] == "'")):
        u = u[1:-1].strip()
    return u.rstrip("/")


class TasksConnector(BaseConnector):
    provider_key = "google_tasks"
    default_scopes = [
        "https://www.googleapis.com/auth/tasks",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def _redirect_uri(self) -> str:
        explicit = _normalize_redirect_uri(os.getenv("GOOGLE_TASKS_CONNECTOR_REDIRECT_URI", ""))
        if explicit:
            return explicit

        cal = _normalize_redirect_uri(os.getenv("GOOGLE_CONNECTOR_REDIRECT_URI", ""))
        if cal and "google_calendar" in cal:
            return cal.replace("google_calendar", "google_tasks", 1)

        raise RuntimeError(
            "Set GOOGLE_TASKS_CONNECTOR_REDIRECT_URI (e.g. http://127.0.0.1:8000/connectors/google_tasks/callback) "
            "or set GOOGLE_CONNECTOR_REDIRECT_URI with …/google_calendar/… so Tasks URL can be derived. "
            "Register the exact Tasks callback URL on the same OAuth Web client as Calendar."
        )
