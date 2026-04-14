"""
Google Calendar OAuth2 (separate client from Supabase login): PKCE + token exchange + revoke.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from services import connector_service as base

logger = logging.getLogger(__name__)

PROVIDER_KEY = "google_calendar"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Least-privilege calendar access for first release
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _oauth_ttl_seconds() -> int:
    return int(_env("CONNECTOR_OAUTH_STATE_TTL_SECONDS", "600") or "600")


def _redirect_uri() -> str:
    uri = _env("GOOGLE_CONNECTOR_REDIRECT_URI")
    if not uri:
        raise RuntimeError("GOOGLE_CONNECTOR_REDIRECT_URI is required for Google Calendar connector")
    return uri


def _client_credentials() -> tuple[str, str]:
    cid = _env("GOOGLE_CONNECTOR_CLIENT_ID")
    csec = _env("GOOGLE_CONNECTOR_CLIENT_SECRET")
    if not cid or not csec:
        raise RuntimeError(
            "GOOGLE_CONNECTOR_CLIENT_ID and GOOGLE_CONNECTOR_CLIENT_SECRET must be set "
            "(separate OAuth client from Supabase login)"
        )
    return cid, csec


def _default_return_to() -> str | None:
    u = _env("FRONTEND_CONNECTOR_BASE_URL")
    return u or None


def build_start_authorization_url(
    user_id: str,
    return_to: str | None,
    login_hint: str | None = None,
) -> tuple[str, str]:
    """
    Returns (authorization_url, state).

    login_hint: Supabase user email passed to Google so the account picker can be skipped when
    it matches the Google session (OAuth 2.0 login_hint parameter).
    """
    _client_credentials()
    oauth_redirect = _redirect_uri()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)

    effective_return = return_to or _default_return_to()

    base.insert_oauth_state(
        state=state,
        user_id=user_id,
        provider_key=PROVIDER_KEY,
        code_verifier=verifier,
        oauth_redirect_uri=oauth_redirect,
        return_to=effective_return,
        ttl_seconds=_oauth_ttl_seconds(),
    )
    base.upsert_user_connector_connecting(user_id, PROVIDER_KEY)

    cid, _ = _client_credentials()
    params: dict[str, str] = {
        "client_id": cid,
        "redirect_uri": oauth_redirect,
        "response_type": "code",
        "scope": " ".join(DEFAULT_SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "include_granted_scopes": "true",
    }
    if base.should_force_google_oauth_consent_prompt(user_id, PROVIDER_KEY):
        params["prompt"] = "consent"
    if login_hint:
        params["login_hint"] = login_hint
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return url, state


def exchange_code_for_tokens_with_verifier(code: str, code_verifier: str, oauth_redirect_uri: str) -> dict[str, Any]:
    cid, csec = _client_credentials()
    data = {
        "client_id": cid,
        "client_secret": csec,
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": oauth_redirect_uri,
    }
    r = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=30)
    if r.status_code != 200:
        logger.warning("Google token exchange failed: %s %s", r.status_code, r.text)
        r.raise_for_status()
    return r.json()


def fetch_user_email(access_token: str) -> tuple[str | None, str | None]:
    try:
        r = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        if r.status_code != 200:
            return None, None
        j = r.json()
        return j.get("id"), j.get("email")
    except Exception as e:
        logger.debug("userinfo fetch failed: %s", e)
        return None, None


def complete_oauth_callback(code: str, state: str) -> tuple[str, bool, str | None]:
    """
    Returns (redirect_url, success, error_message).
    """
    row = base.consume_oauth_state(state)
    if not row:
        url = _failure_redirect(None, "invalid_or_expired_state")
        return url, False, "invalid_or_expired_state"

    return_to = row.get("return_to")
    user_id = row["user_id"]
    code_verifier = row["code_verifier"]
    oauth_redirect_uri = row["oauth_redirect_uri"]

    try:
        token_payload = exchange_code_for_tokens_with_verifier(code, code_verifier, oauth_redirect_uri)
    except Exception as e:
        logger.exception("token exchange failed")
        base.mark_connector_error(user_id, PROVIDER_KEY, str(e))
        return _failure_redirect(return_to, "token_exchange_failed"), False, str(e)

    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in")
    if not access_token:
        base.mark_connector_error(user_id, PROVIDER_KEY, "missing_access_token")
        return _failure_redirect(return_to, "missing_access_token"), False, "missing_access_token"

    expires_at = None
    if expires_in is not None:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            pass

    ext_id, email = fetch_user_email(access_token)

    uc_id = base.get_user_connector_id(user_id, PROVIDER_KEY)
    if not uc_id:
        uc_id = base.upsert_user_connector_connecting(user_id, PROVIDER_KEY)

    base.save_tokens_for_connector(uc_id, access_token, refresh_token, expires_at)
    base.mark_connector_connected(
        user_id,
        PROVIDER_KEY,
        scopes=list(DEFAULT_SCOPES),
        external_account_id=ext_id,
        provider_email=email,
    )

    return _success_redirect(return_to), True, None


def oauth_error_callback(state: str | None, oauth_error: str) -> str:
    """Google redirected with ?error=... — consume state and mark connector error."""
    row = base.consume_oauth_state(state) if state else None
    return_to = row.get("return_to") if row else None
    user_id = row.get("user_id") if row else None
    if user_id:
        base.mark_connector_error(user_id, PROVIDER_KEY, oauth_error)
    return _failure_redirect(return_to, oauth_error or "oauth_error")


def _success_redirect(return_to: str | None) -> str:
    return _append_query(return_to, {"connector_status": "success", "provider": PROVIDER_KEY})


def _failure_redirect(return_to: str | None, reason: str) -> str:
    return _append_query(return_to, {"connector_status": "error", "provider": PROVIDER_KEY, "reason": reason})


def _append_query(url: str | None, params: dict[str, str]) -> str:
    base_url = url or _default_return_to() or "http://localhost:8081"
    parts = urllib.parse.urlparse(base_url)
    q = dict(urllib.parse.parse_qsl(parts.query))
    q.update(params)
    new_query = urllib.parse.urlencode(q)
    return urllib.parse.urlunparse(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            parts.params,
            new_query,
            parts.fragment,
        )
    )


def revoke_and_disconnect(user_id: str) -> None:
    info = base.delete_tokens_and_disconnect(user_id, PROVIDER_KEY)
    if not info:
        return
    token = info.get("refresh_token") or ""
    if not token:
        return
    try:
        requests.post(GOOGLE_REVOKE_URL, data={"token": token}, timeout=15)
    except Exception as e:
        logger.warning("Google revoke failed (token may already be invalid): %s", e)
