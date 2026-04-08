"""
Central configuration for connector providers.

Each provider has a unique key, OAuth scopes, and Google API endpoints.
"""

# ─── Provider Keys ───────────────────────────────────────────────────────────

GOOGLE_CALENDAR_PROVIDER_KEY = "google_calendar"
GOOGLE_TASKS_PROVIDER_KEY = "google_tasks"

# ─── Google OAuth Endpoints ──────────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# ─── Scopes (read + write) ──────────────────────────────────────────────────

GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",          # full read/write
    "https://www.googleapis.com/auth/calendar.events",   # events read/write
]

GOOGLE_TASKS_SCOPES = [
    "https://www.googleapis.com/auth/tasks",             # full read/write
]

# ─── Provider Metadata ──────────────────────────────────────────────────────

PROVIDER_CONFIG = {
    GOOGLE_CALENDAR_PROVIDER_KEY: {
        "display_name": "Google Calendar",
        "scopes": GOOGLE_CALENDAR_SCOPES,
        "health_check_url": "https://www.googleapis.com/calendar/v3/calendars/primary",
        "slug": "google-calendar",  # URL-friendly slug
    },
    GOOGLE_TASKS_PROVIDER_KEY: {
        "display_name": "Google Tasks",
        "scopes": GOOGLE_TASKS_SCOPES,
        "health_check_url": "https://tasks.googleapis.com/tasks/v1/users/@me/lists",
        "slug": "google-tasks",  # URL-friendly slug
    },
}

# Reverse map: slug → provider_key
SLUG_TO_PROVIDER_KEY = {v["slug"]: k for k, v in PROVIDER_CONFIG.items()}
