"""
FastAPI dependency for extracting and validating the current user
from the Authorization header.

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

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Decode the JWT from the Authorization header and return the token payload.
    Raises 401 if the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        # Supabase JWTs use 'authenticated' as an audience
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=[JWT_ALGORITHM], audience="authenticated")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except (jwt.InvalidTokenError, KeyError, ValueError) as err:
        print(f"Token error: {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
