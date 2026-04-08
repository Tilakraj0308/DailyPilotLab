"""
Connectors service — business logic for OAuth connector management.

Handles:
- Token CRUD with encryption at rest
- Google OAuth code exchange
- Google identity resolution (userinfo)
- Access token refresh with revocation detection
- Google Calendar event fetching with retry logic

Follows the project pattern: Service → DB (psycopg2 raw SQL)
"""

import os
import requests as http_requests
from datetime import datetime, timezone, timedelta
from db.dbConnection import get_dict_cursor
from utils.crypto import (
    encrypt_tokens,
    decrypt_tokens,
    encrypt_single_token,
    create_oauth_state,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

# Read-only calendar scope + user identity scopes
GOOGLE_CALENDAR_SCOPES = "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile"

# Refresh proactively if token expires within this window
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class ConnectorRevokedException(Exception):
    """Raised when a connector's tokens are revoked or invalid."""
    pass


class ConnectorRateLimitException(Exception):
    """Raised when Google API returns 429."""
    pass


class ConnectorUnavailableException(Exception):
    """Raised when Google API returns 5xx."""
    pass


# ---------------------------------------------------------------------------
# User Resolution
# ---------------------------------------------------------------------------

def get_user_id_from_auth(auth_id: str) -> int | None:
    """
    Resolve a Supabase auth_id (JWT 'sub') to the internal users.id.
    Returns None if the user doesn't exist.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT id FROM public.users WHERE auth_id = %s",
            (auth_id,),
        )
        row = cur.fetchone()
        return row["id"] if row else None


# ---------------------------------------------------------------------------
# OAuth URL Generation
# ---------------------------------------------------------------------------

def build_google_auth_url(user_id: int, deep_link: str = None) -> str:
    """
    Build the Google OAuth consent URL with a signed state parameter.
    The state encodes user_id + expiry + HMAC signature + optional deep_link.
    """
    state = create_oauth_state(user_id, deep_link)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_CALENDAR_SCOPES,
        "access_type": "offline",        # Required for refresh_token
        "prompt": "consent",             # Force consent to always get refresh_token
        "state": state,
    }

    import urllib.parse
    query = urllib.parse.urlencode(params)
    return f"{GOOGLE_AUTH_URL}?{query}"


# ---------------------------------------------------------------------------
# OAuth Code Exchange
# ---------------------------------------------------------------------------

def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange an authorization code for access + refresh tokens.

    Returns:
        {
            "access_token": str,
            "refresh_token": str,
            "expires_in": int,      # seconds
            "scope": str,
            "token_type": str,
        }

    Raises:
        ValueError: if the exchange fails.
    """
    response = http_requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )

    if response.status_code != 200:
        error_detail = response.json().get("error_description", response.text)
        raise ValueError(f"Token exchange failed: {error_detail}")

    data = response.json()
    if "refresh_token" not in data:
        raise ValueError(
            "No refresh_token returned. User may have previously connected "
            "without revoking. Prompt with prompt=consent next time."
        )

    return data


# ---------------------------------------------------------------------------
# Google Identity
# ---------------------------------------------------------------------------

def fetch_google_identity(access_token: str) -> dict:
    """
    Fetch the connected Google account's identity.

    Returns:
        {"id": "google-sub-id", "email": "user@gmail.com"}

    Raises:
        ValueError: if the userinfo call fails.
    """
    response = http_requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )

    if response.status_code != 200:
        raise ValueError(f"Failed to fetch Google identity: {response.status_code}")

    data = response.json()
    return {
        "id": data.get("id", ""),
        "email": data.get("email", ""),
    }


# ---------------------------------------------------------------------------
# Connector CRUD
# ---------------------------------------------------------------------------

def upsert_connector(
    user_id: int,
    provider: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    scopes: str,
    provider_account_id: str,
    provider_account_email: str,
) -> dict:
    """
    Encrypt tokens and upsert the connector row.
    On conflict (same user+provider), update all token fields and clear revoked_at.
    """
    access_enc, refresh_enc, nonce = encrypt_tokens(access_token, refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    scope_list = [s.strip() for s in scopes.split(" ") if s.strip()]

    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.connectors (
                user_id, provider, provider_account_id, provider_account_email,
                scopes, access_token_enc, refresh_token_enc, token_nonce,
                expires_at, connected_at, revoked_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, now(), NULL
            )
            ON CONFLICT (user_id, provider) DO UPDATE SET
                provider_account_id = EXCLUDED.provider_account_id,
                provider_account_email = EXCLUDED.provider_account_email,
                scopes = EXCLUDED.scopes,
                access_token_enc = EXCLUDED.access_token_enc,
                refresh_token_enc = EXCLUDED.refresh_token_enc,
                token_nonce = EXCLUDED.token_nonce,
                expires_at = EXCLUDED.expires_at,
                connected_at = now(),
                revoked_at = NULL
            RETURNING id, provider, connected_at
            """,
            (
                user_id, provider, provider_account_id, provider_account_email,
                scope_list, access_enc, refresh_enc, nonce,
                expires_at,
            ),
        )
        row = cur.fetchone()
        return dict(row) if row else {}


def get_connector_status(user_id: int, provider: str) -> dict | None:
    """
    Get the status of a connector (without decrypting tokens).
    Returns None if no connector row exists.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT provider, provider_account_email, scopes,
                   expires_at, connected_at, last_sync_at, revoked_at
            FROM public.connectors
            WHERE user_id = %s AND provider = %s
            """,
            (user_id, provider),
        )
        row = cur.fetchone()
        if not row:
            return None

        row = dict(row)
        row["connected"] = row["revoked_at"] is None and row.get("connected_at") is not None
        row["needs_reconnect"] = row["revoked_at"] is not None
        return row


def get_all_connectors(user_id: int) -> list[dict]:
    """Get all connector statuses for a user."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT provider, provider_account_email, scopes,
                   expires_at, connected_at, last_sync_at, revoked_at
            FROM public.connectors
            WHERE user_id = %s
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        result = []
        for row in rows:
            row = dict(row)
            row["connected"] = row["revoked_at"] is None and row.get("connected_at") is not None
            row["needs_reconnect"] = row["revoked_at"] is not None
            result.append(row)
        return result


def revoke_connector(user_id: int, provider: str) -> bool:
    """
    Disconnect a connector: set revoked_at and clear token fields.
    Returns True if a row was updated.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.connectors
            SET revoked_at = now(),
                access_token_enc = NULL,
                refresh_token_enc = NULL,
                token_nonce = NULL,
                expires_at = NULL
            WHERE user_id = %s AND provider = %s AND revoked_at IS NULL
            RETURNING id
            """,
            (user_id, provider),
        )
        row = cur.fetchone()
        return row is not None


# ---------------------------------------------------------------------------
# Token Decryption & Refresh
# ---------------------------------------------------------------------------

def get_decrypted_tokens(user_id: int, provider: str) -> tuple[str, str]:
    """
    Decrypt and return (access_token, refresh_token) for a connector.

    Raises:
        ConnectorRevokedException: if the connector is revoked or tokens are missing.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT access_token_enc, refresh_token_enc, token_nonce, revoked_at
            FROM public.connectors
            WHERE user_id = %s AND provider = %s
            """,
            (user_id, provider),
        )
        row = cur.fetchone()

    if not row:
        raise ConnectorRevokedException("Connector not found")

    if row["revoked_at"] is not None:
        raise ConnectorRevokedException("Connector has been revoked")

    if not row["access_token_enc"] or not row["refresh_token_enc"] or not row["token_nonce"]:
        raise ConnectorRevokedException("Connector tokens are missing — reconnect required")

    return decrypt_tokens(
        bytes(row["access_token_enc"]),
        bytes(row["refresh_token_enc"]),
        bytes(row["token_nonce"]),
    )


def is_token_expiring_soon(user_id: int, provider: str) -> bool:
    """Check if the access token expires within the buffer window."""
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT expires_at FROM public.connectors WHERE user_id = %s AND provider = %s",
            (user_id, provider),
        )
        row = cur.fetchone()
        if not row or not row["expires_at"]:
            return True  # No expiry info → treat as expiring

        expires_at = row["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) + TOKEN_REFRESH_BUFFER >= expires_at


def refresh_access_token(user_id: int, provider: str) -> bool:
    """
    Refresh the access token using the stored refresh token.

    On success: encrypts new access token, updates expires_at.
    On failure (revoked refresh token): marks connector as revoked.

    Returns:
        True if refresh succeeded, False if the connector is now revoked.
    """
    try:
        _, refresh_token = get_decrypted_tokens(user_id, provider)
    except ConnectorRevokedException:
        return False

    response = http_requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )

    if response.status_code != 200:
        # Refresh token is invalid/revoked
        print(f"Token refresh failed for user {user_id}: {response.status_code} {response.text}")
        mark_connector_revoked(user_id, provider)
        return False

    data = response.json()
    new_access_token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    # Get current nonce to re-encrypt with a fresh nonce
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT refresh_token_enc FROM public.connectors WHERE user_id = %s AND provider = %s",
            (user_id, provider),
        )
        row = cur.fetchone()

    # Re-encrypt both tokens with a new nonce
    new_access_enc, new_refresh_enc, new_nonce = encrypt_tokens(new_access_token, refresh_token)

    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.connectors
            SET access_token_enc = %s,
                refresh_token_enc = %s,
                token_nonce = %s,
                expires_at = %s
            WHERE user_id = %s AND provider = %s
            """,
            (new_access_enc, new_refresh_enc, new_nonce, new_expires_at, user_id, provider),
        )

    return True


def mark_connector_revoked(user_id: int, provider: str) -> None:
    """Mark a connector as revoked (access denied by Google)."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.connectors
            SET revoked_at = now(),
                access_token_enc = NULL,
                refresh_token_enc = NULL,
                token_nonce = NULL,
                expires_at = NULL
            WHERE user_id = %s AND provider = %s
            """,
            (user_id, provider),
        )


# ---------------------------------------------------------------------------
# Calendar Events
# ---------------------------------------------------------------------------

def fetch_calendar_events(
    user_id: int,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 50,
) -> list[dict]:
    """
    Fetch calendar events from Google Calendar API.

    Handles:
    - Pre-flight token refresh if expiring soon
    - 401 → refresh → retry once
    - 403 → mark revoked
    - 429 → raise rate limit exception

    Args:
        user_id: Internal user ID
        time_min: ISO datetime lower bound (default: now)
        time_max: ISO datetime upper bound (default: 7 days from now)
        max_results: Maximum events to return

    Returns:
        List of CalendarEvent-compatible dicts

    Raises:
        ConnectorRevokedException: if tokens are invalid/revoked
        ConnectorRateLimitException: if Google returns 429
        ConnectorUnavailableException: if Google returns 5xx
    """
    provider = "google_calendar"

    # Pre-flight: refresh if expiring soon
    if is_token_expiring_soon(user_id, provider):
        if not refresh_access_token(user_id, provider):
            raise ConnectorRevokedException("Reconnect required — refresh token expired")

    access_token, _ = get_decrypted_tokens(user_id, provider)

    # Default time range: now → 7 days
    if not time_min:
        time_min = datetime.now(timezone.utc).isoformat()
    if not time_max:
        time_max = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    response = _call_calendar_api(access_token, time_min, time_max, max_results)

    # Handle 401: refresh and retry once
    if response.status_code == 401:
        if not refresh_access_token(user_id, provider):
            raise ConnectorRevokedException("Reconnect required — token revoked")
        access_token, _ = get_decrypted_tokens(user_id, provider)
        response = _call_calendar_api(access_token, time_min, time_max, max_results)

    # Handle error responses
    if response.status_code == 403:
        mark_connector_revoked(user_id, provider)
        raise ConnectorRevokedException("Access revoked by Google")

    if response.status_code == 429:
        raise ConnectorRateLimitException("Google Calendar API rate limit — try again later")

    if response.status_code >= 500:
        raise ConnectorUnavailableException("Google Calendar API temporarily unavailable")

    if response.status_code != 200:
        raise Exception(f"Unexpected Google Calendar API error: {response.status_code}")

    # Update last_sync_at
    with get_dict_cursor() as cur:
        cur.execute(
            "UPDATE public.connectors SET last_sync_at = now() WHERE user_id = %s AND provider = %s",
            (user_id, provider),
        )

    return _parse_events(response.json())


def _call_calendar_api(
    access_token: str,
    time_min: str,
    time_max: str,
    max_results: int,
) -> http_requests.Response:
    """Make the actual HTTP call to Google Calendar API."""
    return http_requests.get(
        GOOGLE_CALENDAR_EVENTS_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
        },
        timeout=15,
    )


def _parse_events(data: dict) -> list[dict]:
    """Parse Google Calendar API response into CalendarEvent-compatible dicts."""
    events = []
    for item in data.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})

        is_all_day = "date" in start
        start_str = start.get("dateTime") or start.get("date", "")
        end_str = end.get("dateTime") or end.get("date", "")

        events.append({
            "id": item.get("id", ""),
            "summary": item.get("summary", "(No title)"),
            "start": start_str,
            "end": end_str,
            "location": item.get("location"),
            "status": item.get("status", "confirmed"),
            "is_all_day": is_all_day,
        })

    return events
