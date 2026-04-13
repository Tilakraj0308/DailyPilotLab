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
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "change-me-in-production")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# Fallback anon key for online verification if ES256 is used
SUPABASE_ANON_KEY = os.getenv(
    "SUPABASE_ANON_KEY", 
    "")

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Decode the JWT from the Authorization header and return the token payload.
    Raises 401 if the token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        
        if alg == "HS256":
            # Verify offline using symmetric secret
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256", "HS384", "HS512"],
                options={"verify_aud": False}
            )
        else:
            # Fallback for ES256/RS256 without JWKS: Verify online via Supabase
            if not SUPABASE_URL:
                raise ValueError("SUPABASE_URL is required for online ES256 verification")
                
            response = requests.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_ANON_KEY
                },
                timeout=5
            )
            
            if response.status_code != 200:
                raise ValueError(f"Online verification failed: {response.text}")
                
            # Since Supabase verified it, we can safely decode the payload
            payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except Exception as err:
        print(f"Token error: {type(err).__name__} - {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def get_current_user_id(payload: dict = Depends(get_current_user)) -> int:
    """
    Resolve the JWT payload to the internal users.id.

    Chains: Authorization header → JWT decode → auth_id → users.id
    Use this as a dependency on any route that needs ownership enforcement.
    """
    from services.connectors_service import get_user_id_from_auth

    auth_id = payload.get("sub", "")
    if not auth_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user identity in token",
        )

    user_id = get_user_id_from_auth(auth_id)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found — please sign in again",
        )

    return user_id
