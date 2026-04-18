"""
Shared OAuth helpers for connector providers (PKCE, redirect URL helpers, env).
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import urllib.parse


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def oauth_ttl_seconds() -> int:
    return int(env("CONNECTOR_OAUTH_STATE_TTL_SECONDS", "600") or "600")


def default_return_to() -> str | None:
    return env("FRONTEND_CONNECTOR_BASE_URL") or None


def append_query(url: str | None, params: dict[str, str]) -> str:
    base_url = url or default_return_to() or "http://localhost:8081"
    parts = urllib.parse.urlparse(base_url)
    q = dict(urllib.parse.parse_qsl(parts.query))
    q.update(params)
    new_query = urllib.parse.urlencode(q)
    return urllib.parse.urlunparse(
        (parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment)
    )
