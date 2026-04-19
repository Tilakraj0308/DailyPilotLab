"""Notion — public integration OAuth (separate from Google)."""

from __future__ import annotations

import base64
import logging
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from connectors import db
from connectors.oauth_common import append_query, default_return_to, env, oauth_ttl_seconds, pkce_pair

logger = logging.getLogger(__name__)

NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

# Default matches common Notion API examples; override with NOTION_API_VERSION if needed.
DEFAULT_NOTION_VERSION = "2022-06-28"


def _normalize_email(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    s = value.strip().lower()
    return s or None


def notion_owner_person_email_from_token_payload(payload: dict[str, Any]) -> str | None:
    """
    Notion token response may include owner.type == "user" with person.email.
    Workspace installs use owner.type == "workspace" — no person email to compare.
    """
    owner = payload.get("owner")
    if not isinstance(owner, dict) or owner.get("type") != "user":
        return None
    inner = owner.get("user")
    if not isinstance(inner, dict):
        return None
    person = inner.get("person")
    if isinstance(person, dict):
        em = person.get("email")
        if isinstance(em, str) and em.strip():
            return em.strip()
    return None


def _notion_oauth_strict_app_email() -> bool:
    v = (env("NOTION_OAUTH_STRICT_APP_EMAIL", "true") or "true").lower()
    return v not in ("0", "false", "no", "off")


def _notion_credentials() -> tuple[str, str]:
    cid = env("NOTION_CLIENT_ID")
    csec = env("NOTION_CLIENT_SECRET")
    if not cid or not csec:
        raise RuntimeError("NOTION_CLIENT_ID and NOTION_CLIENT_SECRET must be set")
    return cid, csec


def _notion_basic_auth_header() -> str:
    cid, csec = _notion_credentials()
    raw = f"{cid}:{csec}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _notion_version() -> str:
    return env("NOTION_API_VERSION", DEFAULT_NOTION_VERSION) or DEFAULT_NOTION_VERSION


def _redirect_uri() -> str:
    uri = env("NOTION_CONNECTOR_REDIRECT_URI", "").strip()
    if not uri:
        raise RuntimeError(
            "NOTION_CONNECTOR_REDIRECT_URI is required "
            "(e.g. http://127.0.0.1:8000/connectors/notion/callback)"
        )
    return uri.rstrip("/")


class NotionConnector:
    """Notion OAuth 2.0 (authorization code). Token endpoint uses HTTP Basic auth."""

    provider_key = "notion"
    # Notion capabilities are configured on the integration; we store a label for display.
    default_scopes = ["notion"]

    def build_start_authorization_url(
        self,
        user_id: str,
        return_to: str | None,
        login_hint: str | None = None,
    ) -> tuple[str, str]:
        _notion_credentials()
        oauth_redirect = _redirect_uri()
        # Store PKCE verifier for DB consistency; Notion authorize URL does not use PKCE.
        verifier, _challenge = pkce_pair()
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

        cid, _ = _notion_credentials()
        params = {
            "client_id": cid,
            "redirect_uri": oauth_redirect,
            "response_type": "code",
            "owner": "user",
            "state": state,
        }
        url = f"{NOTION_AUTH_URL}?{urllib.parse.urlencode(params)}"
        return url, state

    def _exchange_code(self, code: str, oauth_redirect_uri: str) -> dict[str, Any]:
        headers = {
            "Authorization": _notion_basic_auth_header(),
            "Content-Type": "application/json",
            "Notion-Version": _notion_version(),
        }
        body = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": oauth_redirect_uri,
        }
        r = requests.post(NOTION_TOKEN_URL, json=body, headers=headers, timeout=30)
        if r.status_code != 200:
            logger.warning("Notion token exchange failed: %s %s", r.status_code, r.text)
            r.raise_for_status()
        return r.json()

    def _refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        headers = {
            "Authorization": _notion_basic_auth_header(),
            "Content-Type": "application/json",
            "Notion-Version": _notion_version(),
        }
        body = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        r = requests.post(NOTION_TOKEN_URL, json=body, headers=headers, timeout=30)
        if r.status_code != 200:
            logger.warning("Notion token refresh failed: %s %s", r.status_code, r.text)
            r.raise_for_status()
        return r.json()

    def complete_oauth_callback(self, code: str, state: str) -> tuple[str, bool, str | None]:
        row = db.consume_oauth_state(state)
        if not row:
            url = self._failure_redirect(None, "invalid_or_expired_state")
            return url, False, "invalid_or_expired_state"

        return_to = row.get("return_to")
        user_id = row["user_id"]
        oauth_redirect_uri = row["oauth_redirect_uri"]

        try:
            token_payload = self._exchange_code(code, oauth_redirect_uri)
        except Exception as e:
            logger.exception("Notion token exchange failed")
            db.mark_connector_error(user_id, self.provider_key, str(e))
            return self._failure_redirect(return_to, "token_exchange_failed"), False, str(e)

        access_token = token_payload.get("access_token")
        refresh_token = token_payload.get("refresh_token")
        bot_id = token_payload.get("bot_id")
        workspace_name = token_payload.get("workspace_name") or token_payload.get("workspace_id")
        expires_in = token_payload.get("expires_in")

        if not access_token:
            db.mark_connector_error(user_id, self.provider_key, "missing_access_token")
            return self._failure_redirect(return_to, "missing_access_token"), False, "missing_access_token"

        if _notion_oauth_strict_app_email():
            app_email = _normalize_email(db.get_user_email_by_auth_id(user_id))
            notion_email = _normalize_email(notion_owner_person_email_from_token_payload(token_payload))
            if app_email and notion_email and app_email != notion_email:
                logger.warning(
                    "Notion OAuth email mismatch: app=%s notion=%s user_id=%s",
                    app_email,
                    notion_email,
                    user_id,
                )
                db.mark_connector_error(user_id, self.provider_key, "notion_account_email_mismatch")
                return (
                    self._failure_redirect(return_to, "notion_account_email_mismatch"),
                    False,
                    "notion_account_email_mismatch",
                )
            if app_email and not notion_email:
                logger.warning(
                    "Notion OAuth: strict email enabled but token has no person email (workspace owner?); "
                    "allowing connection user_id=%s",
                    user_id,
                )

        expires_at = None
        if expires_in is not None:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError):
                pass

        ext_id = str(bot_id) if bot_id else None
        display = workspace_name if isinstance(workspace_name, str) else None

        uc_id = db.get_user_connector_id(user_id, self.provider_key)
        if not uc_id:
            uc_id = db.upsert_user_connector_connecting(user_id, self.provider_key)

        db.save_tokens_for_connector(uc_id, access_token, refresh_token, expires_at)
        db.mark_connector_connected(
            user_id,
            self.provider_key,
            scopes=list(self.default_scopes),
            external_account_id=ext_id,
            provider_email=display,
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
        # Notion has no documented token revoke URL for integrations; clear local state only.
        db.delete_tokens_and_disconnect(user_id, self.provider_key)

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
            raise RuntimeError("Re-authentication required")

        try:
            payload = self._refresh_tokens(refresh)
        except Exception as e:
            db.mark_connector_reauth(user_id, self.provider_key, str(e))
            raise RuntimeError("Token refresh failed") from e

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
