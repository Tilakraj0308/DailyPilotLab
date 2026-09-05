"""
Google OAuth connector — Calendar / Tasks / Gmail shared OAuth lifecycle.

Other providers use separate connector classes; this module stays Google-specific.
"""

from __future__ import annotations

import logging
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from connectors import db
from connectors.oauth_common import (
    append_query,
    default_return_to,
    env,
    oauth_ttl_seconds,
    pkce_pair,
)

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class ConnectorReAuthError(Exception):
    """Raised when access token is expired and refresh token strategy fails or is missing."""

    def __init__(self, provider_key: str, message: str):
        super().__init__(message)
        self.provider_key = provider_key
        self.message = message


def _client_credentials() -> tuple[str, str]:
    cid = env("GOOGLE_CONNECTOR_CLIENT_ID")
    csec = env("GOOGLE_CONNECTOR_CLIENT_SECRET")
    if not cid or not csec:
        raise RuntimeError(
            "GOOGLE_CONNECTOR_CLIENT_ID and GOOGLE_CONNECTOR_CLIENT_SECRET must be set"
        )
    return cid, csec


class GoogleOAuthConnector:
    """
    Google OAuth 2.0 PKCE flow for Calendar / Tasks.
    """

    provider_key: str
    default_scopes: list[str]

    def _redirect_uri(self) -> str:
        raise NotImplementedError

    def build_start_authorization_url(
        self,
        user_id: str,
        return_to: str | None,
        login_hint: str | None = None,
    ) -> tuple[str, str]:
        _client_credentials()
        oauth_redirect = self._redirect_uri()
        verifier, challenge = pkce_pair()
        state = secrets.token_urlsafe(32)
        effective_return = return_to or default_return_to()

        db.insert_oauth_state(
            state=state,
            user_id=user_id,
            provider_key=self.provider_key,
            code_verifier=verifier,
            oauth_redirect_uri=oauth_redirect,
            return_to=effective_return,
            ttl_seconds=oauth_ttl_seconds(),
        )
        db.upsert_user_connector_connecting(user_id, self.provider_key)

        cid, _ = _client_credentials()
        params: dict[str, str] = {
            "client_id": cid,
            "redirect_uri": oauth_redirect,
            "response_type": "code",
            "scope": " ".join(self.default_scopes),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "include_granted_scopes": "true",
        }
        if db.should_force_google_oauth_consent_prompt(user_id, self.provider_key):
            params["prompt"] = "consent"
        if login_hint:
            params["login_hint"] = login_hint
        url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return url, state

    def exchange_code_for_tokens_with_verifier(self, code: str, code_verifier: str, oauth_redirect_uri: str) -> dict[str, Any]:
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

    def fetch_user_email(self, access_token: str) -> tuple[str | None, str | None]:
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

    def complete_oauth_callback(self, code: str, state: str) -> tuple[str, bool, str | None]:
        row = db.consume_oauth_state(state)
        if not row:
            url = self._failure_redirect(None, "invalid_or_expired_state")
            return url, False, "invalid_or_expired_state"

        return_to = row.get("return_to")
        user_id = row["user_id"]
        code_verifier = row["code_verifier"]
        oauth_redirect_uri = row["oauth_redirect_uri"]

        try:
            token_payload = self.exchange_code_for_tokens_with_verifier(code, code_verifier, oauth_redirect_uri)
        except Exception as e:
            logger.exception("token exchange failed")
            db.mark_connector_error(user_id, self.provider_key, str(e))
            return self._failure_redirect(return_to, "token_exchange_failed"), False, str(e)

        access_token = token_payload.get("access_token")
        refresh_token = token_payload.get("refresh_token")
        expires_in = token_payload.get("expires_in")
        if not access_token:
            db.mark_connector_error(user_id, self.provider_key, "missing_access_token")
            return self._failure_redirect(return_to, "missing_access_token"), False, "missing_access_token"

        expires_at = None
        if expires_in is not None:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError):
                pass

        ext_id, email = self.fetch_user_email(access_token)

        uc_id = db.get_user_connector_id(user_id, self.provider_key)
        if not uc_id:
            uc_id = db.upsert_user_connector_connecting(user_id, self.provider_key)

        db.save_tokens_for_connector(uc_id, access_token, refresh_token, expires_at)
        db.mark_connector_connected(
            user_id,
            self.provider_key,
            scopes=list(self.default_scopes),
            external_account_id=ext_id,
            provider_email=email,
        )
        db.init_default_permissions(user_id, self.provider_key)

        return self._success_redirect(return_to), True, None

    def oauth_error_callback(self, state: str | None, oauth_error: str) -> str:
        row = db.consume_oauth_state(state) if state else None
        return_to = row.get("return_to") if row else None
        user_id = row.get("user_id") if row else None
        if user_id:
            db.mark_connector_error(user_id, self.provider_key, oauth_error)
        return self._failure_redirect(return_to, oauth_error or "oauth_error")

    def _success_redirect(self, return_to: str | None) -> str:
        return append_query(return_to, {"connector_status": "success", "provider": self.provider_key})

    def _failure_redirect(self, return_to: str | None, reason: str) -> str:
        return append_query(
            return_to,
            {"connector_status": "error", "provider": self.provider_key, "reason": reason},
        )

    def revoke_and_disconnect(self, user_id: str) -> None:
        info = db.delete_tokens_and_disconnect(user_id, self.provider_key)
        if not info:
            return
        token = info.get("refresh_token") or ""
        if not token:
            return
        try:
            requests.post(GOOGLE_REVOKE_URL, data={"token": token}, timeout=15)
        except Exception as e:
            logger.warning("Google revoke failed (token may already be invalid): %s", e)

    def _refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        cid, csec = _client_credentials()
        r = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": cid,
                "client_secret": csec,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if r.status_code != 200:
            logger.warning("Token refresh failed: %s %s", r.status_code, r.text)
            r.raise_for_status()
        return r.json()

    def ensure_access_token(self, user_id: str) -> str:
        bundle = db.get_connector_token_bundle(user_id, self.provider_key)
        if not bundle:
            raise RuntimeError(f"{self.provider_key} not connected")

        access = bundle["access_token"]
        refresh = bundle["refresh_token"]
        expires_at = bundle["token_expires_at"]
        uc_id = bundle["user_connector_id"]

        now = datetime.now(timezone.utc)
        if expires_at is not None:
            if getattr(expires_at, "tzinfo", None) is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at > now + timedelta(minutes=2):
                return access
        elif access:
            return access

        if not refresh:
            db.mark_connector_reauth(user_id, self.provider_key, "missing_refresh_token")
            raise ConnectorReAuthError(self.provider_key, "Re-authentication required: missing refresh token")

        try:
            payload = self._refresh_access_token(refresh)
        except Exception as e:
            db.mark_connector_reauth(user_id, self.provider_key, str(e))
            raise ConnectorReAuthError(self.provider_key, f"Token refresh failed: {e}") from e

        new_access = payload.get("access_token")
        new_refresh = payload.get("refresh_token") or refresh
        expires_in = payload.get("expires_in")
        new_expires = None
        if expires_in is not None:
            try:
                new_expires = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError):
                pass
        if not new_access:
            raise RuntimeError("No access token after refresh")

        db.save_tokens_for_connector(uc_id, new_access, new_refresh, new_expires)
        return new_access


# Backward compatibility for google_calendar / google_tasks connectors
BaseConnector = GoogleOAuthConnector
