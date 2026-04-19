"""
FastAPI dependency for extracting and validating the current user
from the Authorization header.

Supabase may sign access tokens with either:
- HS256 + legacy JWT secret (legacy / shared-secret projects), or
- ES256/RS256 + JWKS (JWT Signing Keys — see https://supabase.com/docs/guides/auth/jwts )

Connector OAuth redirects do not affect this — JWT verification happens on the first API call
(POST /connectors/.../start) before any redirect to Google.
"""

from __future__ import annotations

import os
import threading

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Legacy JWT secret (HS256 only). Trim whitespace.
_raw_jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "change-me-in-production") or ""
SUPABASE_JWT_SECRET = _raw_jwt_secret.strip()

# JWKS URL for asymmetric tokens (ES256/RS256). Set SUPABASE_URL or SUPABASE_JWKS_URL.
SUPABASE_JWKS_URL = (os.getenv("SUPABASE_JWKS_URL") or "").strip()
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")

JWT_ALGORITHM_HS256 = "HS256"

security = HTTPBearer()

# PyJWKClient is safe to cache per URL (it caches JWKS internally).
_jwks_lock = threading.Lock()
_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks_url() -> str | None:
    if SUPABASE_JWKS_URL:
        return SUPABASE_JWKS_URL
    if SUPABASE_URL:
        return f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    return None


def _get_jwks_client(url: str) -> PyJWKClient:
    with _jwks_lock:
        if url not in _jwks_clients:
            _jwks_clients[url] = PyJWKClient(url)
        return _jwks_clients[url]


def _decode_with_jwks(token: str, alg: str) -> dict:
    url = _jwks_url()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"JWT uses algorithm {alg} (asymmetric). Add SUPABASE_URL (same as EXPO_PUBLIC_SUPABASE_URL) "
                "or SUPABASE_JWKS_URL to server/.env so the API can verify tokens via JWKS. "
                "Example JWKS: https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json"
            ),
        )
    try:
        jwks_client = _get_jwks_client(url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience="authenticated",
        )
    except (jwt.exceptions.PyJWKClientError, OSError) as e:
        print(f"JWKS error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify JWT: JWKS fetch failed. Check SUPABASE_URL and network.",
        ) from e


def decode_supabase_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase access token (HS256 or asymmetric via JWKS).
    """
    if not SUPABASE_JWT_SECRET or SUPABASE_JWT_SECRET == "change-me-in-production":
        print("auth: SUPABASE_JWT_SECRET is missing or still the placeholder — HS256 verification will fail.")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: malformed JWT",
        ) from e

    alg = (header.get("alg") or JWT_ALGORITHM_HS256).upper()

    if alg == JWT_ALGORITHM_HS256:
        try:
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=[JWT_ALGORITHM_HS256],
                audience="authenticated",
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired — sign out and sign in again.",
            ) from None
        except jwt.InvalidSignatureError:
            print("Token error: HS256 signature verification failed (wrong SUPABASE_JWT_SECRET?)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Invalid token: JWT signature failed. If your project uses HS256, set SUPABASE_JWT_SECRET "
                    "to the JWT Secret from Supabase → Project Settings → API. "
                    "If your project uses JWT Signing Keys (ES256), set SUPABASE_URL in server/.env instead."
                ),
            ) from None
        except jwt.InvalidAudienceError as err:
            print(f"Token error (audience): {err}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: audience mismatch — use a Supabase session access token.",
            ) from None
        except (jwt.InvalidTokenError, KeyError, ValueError) as err:
            print(f"Token error: {err}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from err

    # Asymmetric (ES256, RS256, etc.)
    if alg not in ("ES256", "RS256", "ES384", "RS512"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unsupported JWT algorithm: {alg}",
        )

    try:
        return _decode_with_jwks(token, alg)
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired — sign out and sign in again.",
        ) from None
    except jwt.InvalidAudienceError as err:
        print(f"Token error (audience): {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: audience mismatch — use a Supabase session access token.",
        ) from None
    except (jwt.InvalidTokenError, KeyError, ValueError) as err:
        print(f"Token error (JWKS path): {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from err


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Decode the JWT from the Authorization header and return the token payload.
    Raises 401 if the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    return decode_supabase_jwt(token)
