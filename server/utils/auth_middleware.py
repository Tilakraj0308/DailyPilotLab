"""
FastAPI dependency for extracting and validating the current user
from the Authorization header.

Verifies Supabase-issued JWTs and maps the Supabase UUID (sub claim)
to the internal integer user ID via external_auth_id.

Usage in any endpoint:
    from utils.auth_middleware import get_current_user

    @app.get("/protected")
    def protected_route(user_id: int = Depends(get_current_user)):
        ...
"""

import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth_service import get_or_create_user

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Decode the Supabase JWT from the Authorization header.
    - Extract the `sub` claim (Supabase user UUID).
    - Look up (or auto-create) the internal user by external_auth_id.
    - Return the internal integer user ID.
    Raises 401 if the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="authenticated",
        )
        supabase_uid = payload["sub"]  # Supabase user UUID

        # Extract user metadata from JWT claims
        user_meta = payload.get("user_metadata", {})
        email = payload.get("email", user_meta.get("email", ""))
        display_name = user_meta.get("full_name") or user_meta.get("name")
        avatar_url = user_meta.get("avatar_url") or user_meta.get("picture")

        # Map Supabase UUID → internal integer user ID (auto-creates on first login)
        user = get_or_create_user(
            external_auth_id=supabase_uid,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        return user["id"]

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
