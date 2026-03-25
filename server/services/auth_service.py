"""
Auth-agnostic authentication service.

Handles user lookup and creation by external_auth_id (provider-agnostic).
JWT verification and issuance are handled by Supabase — this module only
manages the internal user record.
"""

from db.dbConnection import get_dict_cursor


def get_or_create_user(
    external_auth_id: str,
    email: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> dict:
    """
    Look up a user by external_auth_id.  If they don't exist, create one.
    Returns the user record as a dict with keys:
        id, external_auth_id, email, display_name, avatar_url
    """
    with get_dict_cursor() as cur:
        # Try to find existing user
        cur.execute(
            "SELECT id, external_auth_id, email, display_name, avatar_url "
            "FROM public.users WHERE external_auth_id = %s",
            (external_auth_id,),
        )
        user = cur.fetchone()

        if user:
            return dict(user)

        # Create new user
        cur.execute(
            """
            INSERT INTO public.users (external_auth_id, email, display_name, avatar_url)
            VALUES (%s, %s, %s, %s)
            RETURNING id, external_auth_id, email, display_name, avatar_url
            """,
            (external_auth_id, email, display_name, avatar_url),
        )
        new_user = cur.fetchone()
        return dict(new_user)
