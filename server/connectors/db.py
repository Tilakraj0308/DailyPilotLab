"""
Base connector lifecycle: DB operations shared by all providers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from db.dbConnection import get_dict_cursor
from connectors.token_manager import encrypt_token, decrypt_token

logger = logging.getLogger(__name__)


def cleanup_expired_oauth_states() -> None:
    with get_dict_cursor() as cur:
        cur.execute("DELETE FROM public.oauth_state_sessions WHERE expires_at < now()")


def get_user_email_by_auth_id(auth_id: str) -> str | None:
    """Primary email stored for this app user (synced from Supabase JWT via /auth/profile)."""
    if not auth_id:
        return None
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT email FROM public.users WHERE auth_id = %s LIMIT 1",
            (auth_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        raw = row.get("email")
        if raw is None:
            return None
        s = str(raw).strip()
        return s or None


def connector_provider_exists(provider_key: str) -> bool:
    """True if `provider_key` is present in `public.connector_providers` (required for OAuth FK)."""
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT 1 FROM public.connector_providers WHERE provider_key = %s LIMIT 1",
            (provider_key,),
        )
        return cur.fetchone() is not None


def insert_oauth_state(
    state: str,
    user_id: str,
    provider_key: str,
    code_verifier: str,
    oauth_redirect_uri: str,
    return_to: str | None,
    ttl_seconds: int,
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.oauth_state_sessions
                (state, user_id, provider_key, code_verifier, oauth_redirect_uri, return_to, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (state, user_id, provider_key, code_verifier, oauth_redirect_uri, return_to, expires_at),
        )


def consume_oauth_state(state: str) -> dict[str, Any] | None:
    cleanup_expired_oauth_states()
    with get_dict_cursor() as cur:
        cur.execute(
            """
            DELETE FROM public.oauth_state_sessions
            WHERE state = %s AND expires_at >= now()
            RETURNING user_id, provider_key, code_verifier, oauth_redirect_uri, return_to
            """,
            (state,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_user_connector_connecting(user_id: str, provider_key: str) -> int:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.user_connectors (user_id, provider_key, status, error_message)
            VALUES (%s, %s, 'connecting', NULL)
            ON CONFLICT (user_id, provider_key)
            DO UPDATE SET
                status = 'connecting',
                error_message = NULL,
                updated_at = now()
            RETURNING id
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()
        return int(row["id"])


def save_tokens_for_connector(
    user_connector_id: int,
    access_token: str,
    refresh_token: str | None,
    expires_at: datetime | None,
) -> None:
    enc_a = encrypt_token(access_token)
    enc_r = encrypt_token(refresh_token) if refresh_token else None

    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.user_connector_tokens
                (user_connector_id, encrypted_access_token, encrypted_refresh_token, token_expires_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_connector_id)
            DO UPDATE SET
                encrypted_access_token = EXCLUDED.encrypted_access_token,
                encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                token_expires_at = EXCLUDED.token_expires_at,
                updated_at = now()
            """,
            (user_connector_id, enc_a, enc_r, expires_at),
        )


def mark_connector_connected(
    user_id: str,
    provider_key: str,
    scopes: list[str],
    external_account_id: str | None,
    provider_email: str | None,
) -> None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.user_connectors
            SET
                status = 'connected',
                scopes = %s,
                external_account_id = %s,
                provider_email = %s,
                connected_at = now(),
                disconnected_at = NULL,
                error_message = NULL,
                updated_at = now()
            WHERE user_id = %s AND provider_key = %s
            """,
            (scopes, external_account_id, provider_email, user_id, provider_key),
        )


def mark_connector_error(user_id: str, provider_key: str, message: str) -> None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.user_connectors
            SET status = 'error', error_message = %s, updated_at = now()
            WHERE user_id = %s AND provider_key = %s
            """,
            (message, user_id, provider_key),
        )


def mark_connector_reauth(user_id: str, provider_key: str, message: str | None = None) -> None:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.user_connectors
            SET status = 'reauth_required', error_message = %s, updated_at = now()
            WHERE user_id = %s AND provider_key = %s
            """,
            (message, user_id, provider_key),
        )


def list_connectors_status(user_id: str) -> list[dict[str, Any]]:
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT
                cp.provider_key,
                cp.display_name,
                COALESCE(uc.status::text, 'disconnected') AS status,
                COALESCE(uc.scopes, '{}') AS scopes,
                uc.connected_at,
                uc.provider_email,
                uc.error_message,
                ucr.resource_id AS selected_resource_id,
                ucr.resource_name AS selected_resource_name
            FROM public.connector_providers cp
            LEFT JOIN public.user_connectors uc
                ON uc.provider_key = cp.provider_key AND uc.user_id = %s
            LEFT JOIN public.user_connector_resources ucr
                ON ucr.user_connector_id = uc.id
                AND ucr.resource_type = 'task_list'
            ORDER BY cp.provider_key
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_connector_token_bundle(user_id: str, provider_key: str) -> dict[str, Any] | None:
    """Decrypt tokens for an active connector row (any status with token row)."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT
                uct.encrypted_access_token,
                uct.encrypted_refresh_token,
                uct.token_expires_at,
                uc.id AS user_connector_id
            FROM public.user_connectors uc
            JOIN public.user_connector_tokens uct ON uct.user_connector_id = uc.id
            WHERE uc.user_id = %s AND uc.provider_key = %s
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()
        if not row:
            return None
        access = decrypt_token(bytes(row["encrypted_access_token"]))
        refresh = None
        if row.get("encrypted_refresh_token"):
            refresh = decrypt_token(bytes(row["encrypted_refresh_token"]))
        return {
            "user_connector_id": int(row["user_connector_id"]),
            "access_token": access,
            "refresh_token": refresh,
            "token_expires_at": row["token_expires_at"],
        }


def get_connector_resource(
    user_id: str,
    provider_key: str,
    resource_type: str,
) -> tuple[str | None, str | None]:
    """Returns (resource_id, resource_name) if present."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT ucr.resource_id, ucr.resource_name
            FROM public.user_connector_resources ucr
            JOIN public.user_connectors uc ON uc.id = ucr.user_connector_id
            WHERE uc.user_id = %s AND uc.provider_key = %s AND ucr.resource_type = %s
            """,
            (user_id, provider_key, resource_type),
        )
        row = cur.fetchone()
        if not row:
            return None, None
        return row.get("resource_id"), row.get("resource_name")


def upsert_selected_task_list(
    user_id: str,
    provider_key: str,
    task_list_id: str,
    task_list_title: str | None,
) -> None:
    uc_id = get_user_connector_id(user_id, provider_key)
    if not uc_id:
        raise ValueError("Connector row not found")
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.user_connector_resources
                (user_connector_id, resource_type, resource_id, resource_name, is_selected)
            VALUES (%s, 'task_list', %s, %s, TRUE)
            ON CONFLICT (user_connector_id, resource_type)
            DO UPDATE SET
                resource_id = EXCLUDED.resource_id,
                resource_name = EXCLUDED.resource_name,
                is_selected = TRUE,
                updated_at = now()
            """,
            (uc_id, task_list_id, task_list_title),
        )


def get_user_connector_id(user_id: str, provider_key: str) -> int | None:
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT id FROM public.user_connectors WHERE user_id = %s AND provider_key = %s",
            (user_id, provider_key),
        )
        row = cur.fetchone()
        return int(row["id"]) if row else None


def should_force_google_oauth_consent_prompt(user_id: str, provider_key: str) -> bool:
    """
    When True, add prompt=consent to the Google authorization URL.

    Omitting prompt lets Google use incremental authorization for the same OAuth client
    (e.g. Tasks after Calendar), which is usually a shorter consent step. We only force
    full consent when the connector is already in a bad auth state.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT uc.status::text AS status
            FROM public.user_connectors uc
            WHERE uc.user_id = %s AND uc.provider_key = %s
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()
    if not row:
        return False
    return row["status"] in ("reauth_required", "error")


def delete_tokens_and_disconnect(user_id: str, provider_key: str) -> dict[str, Any] | None:
    """Returns decrypted refresh_token if present (for provider revoke)."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT uct.encrypted_refresh_token, uc.id AS cid
            FROM public.user_connectors uc
            LEFT JOIN public.user_connector_tokens uct ON uct.user_connector_id = uc.id
            WHERE uc.user_id = %s AND uc.provider_key = %s
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()
        if not row:
            return None
        refresh_plain = ""
        if row.get("encrypted_refresh_token"):
            refresh_plain = decrypt_token(bytes(row["encrypted_refresh_token"]))

        cur.execute(
            """
            DELETE FROM public.user_connector_resources
            WHERE user_connector_id = %s
            """,
            (row["cid"],),
        )
        cur.execute(
            """
            DELETE FROM public.user_connector_tokens
            WHERE user_connector_id = %s
            """,
            (row["cid"],),
        )
        cur.execute(
            """
            UPDATE public.user_connectors
            SET
                status = 'disconnected',
                disconnected_at = now(),
                scopes = '{}',
                external_account_id = NULL,
                provider_email = NULL,
                error_message = NULL,
                updated_at = now()
            WHERE user_id = %s AND provider_key = %s
            """,
            (user_id, provider_key),
        )
        return {"refresh_token": refresh_plain or None}


# ─── Tool Permission Helpers ────────────────────────────────────────────────


def list_connected_providers(user_id: str) -> list[str]:
    """Return provider_keys where the user's status is 'connected'."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT provider_key
            FROM public.user_connectors
            WHERE user_id = %s AND status = 'connected'
            ORDER BY provider_key
            """,
            (user_id,),
        )
        return [row["provider_key"] for row in cur.fetchall()]


def get_tool_permissions(user_id: str, provider_key: str) -> dict[str, bool]:
    """
    Return CRUD permission toggles, e.g. {"create": True, "read": True, "update": True, "delete": False}.
    Defaults to all-enabled if no rows exist yet.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT allowed_cruds
            FROM public.connector_tool_permissions
            WHERE user_id = %s AND provider_key = %s
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()

    # Default fallback if no row exists
    defaults = {"create": True, "read": True, "update": True, "delete": True}
    if not row:
        return defaults

    allowed = row.get("allowed_cruds") or []
    # Convert list of strings/enums to the dict format expected by callers
    return {
        "create": "create" in allowed,
        "read": "read" in allowed,
        "update": "update" in allowed,
        "delete": "delete" in allowed,
    }


def update_tool_permission(
    user_id: str, provider_key: str, crud_type: str, enabled: bool
) -> None:
    """Add or remove a single CRUD permission from the array."""
    with get_dict_cursor() as cur:
        if enabled:
            # Add to array uniquely
            cur.execute(
                """
                INSERT INTO public.connector_tool_permissions (user_id, provider_key, allowed_cruds)
                VALUES (%s, %s, ARRAY[%s]::public.tool_crud_type[])
                ON CONFLICT (user_id, provider_key)
                DO UPDATE SET 
                    allowed_cruds = ARRAY(
                        SELECT DISTINCT e FROM unnest(array_append(public.connector_tool_permissions.allowed_cruds, %s::public.tool_crud_type)) e
                    ),
                    updated_at = now()
                """,
                (user_id, provider_key, crud_type, crud_type),
            )
        else:
            # Remove from array
            cur.execute(
                """
                UPDATE public.connector_tool_permissions
                SET allowed_cruds = array_remove(allowed_cruds, %s::public.tool_crud_type),
                    updated_at = now()
                WHERE user_id = %s AND provider_key = %s
                """,
                (crud_type, user_id, provider_key),
            )


def init_default_permissions(user_id: str, provider_key: str) -> None:
    """Seed default CRUD permissions after a successful OAuth connection."""
    # Delete disabled by default for safety
    defaults = ["read", "create", "update"]
    with get_dict_cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.connector_tool_permissions (user_id, provider_key, allowed_cruds)
            VALUES (%s, %s, %s::public.tool_crud_type[])
            ON CONFLICT (user_id, provider_key) DO NOTHING
            """,
            (user_id, provider_key, defaults),
        )
