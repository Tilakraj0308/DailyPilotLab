"""
Authentication service for Google OAuth.

Handles:
- Verifying Google ID tokens
- Creating / retrieving users from the database
- Issuing app-level JWT tokens
"""

# import os
# import jwt
# import datetime

# from google.oauth2 import id_token as google_id_token
# from google.auth.transport import requests as google_requests

from db.dbConnection import get_dict_cursor

# GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
# JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
# JWT_ALGORITHM = "HS256"
# JWT_EXPIRATION_HOURS = 24 * 7  # 7 days


# def verify_google_token(token: str) -> dict:
#     """
#     Verify a Google ID token and return the decoded user info.

#     Returns a dict with keys: sub, email, name, picture (among others).
#     Raises ValueError if the token is invalid.
#     """
#     try:
#         id_info = google_id_token.verify_oauth2_token(
#             token,
#             google_requests.Request(),
#             GOOGLE_CLIENT_ID,
#         )

#         if id_info["iss"] not in ("accounts.google.com", "https://accounts.google.com"):
#             raise ValueError("Invalid issuer.")

#         return id_info
#     except Exception as e:
#         raise ValueError(f"Invalid Google token: {e}")


def get_or_create_user(google_id: str, email: str, display_name: str | None, avatar_url: str | None) -> dict:
    """
    Look up a user by google_id. If they don't exist, create one.
    Returns the user record as a dict.
    """
    with get_dict_cursor() as cur:
        # Try to find existing user
        cur.execute(
            "SELECT id, google_id, email, display_name, avatar_url FROM public.users WHERE google_id = %s",
            (google_id,),
        )
        user = cur.fetchone()

        if user:
            return dict(user)

        # Create new user
        cur.execute(
            """
            INSERT INTO public.users (google_id, email, display_name, avatar_url)
            VALUES (%s, %s, %s, %s)
            RETURNING id, google_id, email, display_name, avatar_url
            """,
            (google_id, email, display_name, avatar_url),
        )
        new_user = cur.fetchone()
        return dict(new_user)


# def create_access_token(user_id: int) -> str:
#     """
#     Generate a JWT containing the user ID with an expiration.
#     """
#     payload = {
#         "sub": str(user_id),
#         "iat": datetime.datetime.now(datetime.timezone.utc),
#         "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
#     }
#     return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
