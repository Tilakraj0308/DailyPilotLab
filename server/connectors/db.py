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
    """True if `provider_key` is present in the in-memory registry."""
    from connectors.providers.registry import SUPPORTED_PROVIDERS
    return provider_key in SUPPORTED_PROVIDERS


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
            UPDATE public.user_connectors
            SET
                access_token = %s,
                refresh_token = %s,
                token_expires_at = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (enc_a, enc_r, expires_at, user_connector_id),
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
    from connectors.providers.registry import SUPPORTED_PROVIDERS
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT
                provider_key,
                status::text AS status,
                scopes,
                connected_at,
                provider_email,
                error_message,
                metadata
            FROM public.user_connectors
            WHERE user_id = %s
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    db_map = {row["provider_key"]: dict(row) for row in rows}

    result = []
    for key, config in SUPPORTED_PROVIDERS.items():
        row = db_map.get(key)
        if row:
            metadata = row.get("metadata") or {}
            task_list = metadata.get("task_list") or {}
            result.append({
                "provider_key": key,
                "display_name": config.display_name,
                "status": row.get("status", "disconnected"),
                "scopes": row.get("scopes", []),
                "connected_at": row.get("connected_at"),
                "provider_email": row.get("provider_email"),
                "error_message": row.get("error_message"),
                "selected_resource_id": task_list.get("id"),
                "selected_resource_name": task_list.get("name"),
            })
        else:
            result.append({
                "provider_key": key,
                "display_name": config.display_name,
                "status": "disconnected",
                "scopes": [],
                "connected_at": None,
                "provider_email": None,
                "error_message": None,
                "selected_resource_id": None,
                "selected_resource_name": None,
            })
    return result


def get_connector_token_bundle(user_id: str, provider_key: str) -> dict[str, Any] | None:
    """Decrypt tokens for an active connector row (any status with token row)."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT
                access_token AS encrypted_access_token,
                refresh_token AS encrypted_refresh_token,
                token_expires_at,
                id AS user_connector_id
            FROM public.user_connectors
            WHERE user_id = %s AND provider_key = %s AND access_token IS NOT NULL
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
            SELECT metadata
            FROM public.user_connectors
            WHERE user_id = %s AND provider_key = %s
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()
        if not row:
            return None, None
        
        metadata = row.get("metadata") or {}
        resource = metadata.get(resource_type) or {}
        return resource.get("id"), resource.get("name")


def upsert_selected_task_list(
    user_id: str,
    provider_key: str,
    task_list_id: str,
    task_list_title: str | None,
) -> None:
    uc_id = get_user_connector_id(user_id, provider_key)
    if not uc_id:
        raise ValueError("Connector row not found")
        
    resource_data = {"id": task_list_id, "name": task_list_title}
    import json
    
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.user_connectors
            SET
                metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{task_list}', %s::jsonb),
                updated_at = now()
            WHERE id = %s
            """,
            (json.dumps(resource_data), uc_id),
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
            SELECT refresh_token AS encrypted_refresh_token, id AS cid
            FROM public.user_connectors
            WHERE user_id = %s AND provider_key = %s
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
            UPDATE public.user_connectors
            SET
                status = 'disconnected',
                disconnected_at = now(),
                scopes = '{}',
                external_account_id = NULL,
                provider_email = NULL,
                error_message = NULL,
                access_token = NULL,
                refresh_token = NULL,
                token_expires_at = NULL,
                metadata = '{}'::jsonb,
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
            SELECT metadata
            FROM public.user_connectors
            WHERE user_id = %s AND provider_key = %s
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()

    defaults = {"create": True, "read": True, "update": True, "delete": True}
    if not row:
        return defaults

    metadata = row.get("metadata") or {}
    perms = metadata.get("permissions")
    if perms is None:
        return defaults

    return {
        "create": perms.get("create", False),
        "read": perms.get("read", False),
        "update": perms.get("update", False),
        "delete": perms.get("delete", False),
    }


def get_all_connected_permissions(user_id: str) -> dict[str, dict[str, bool]]:
    """
    Return CRUD permissions for all connected providers in a single query.
    Returns: { provider_key: { "create": bool, "read": bool, ... } }
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT provider_key, metadata
            FROM public.user_connectors
            WHERE user_id = %s AND status = 'connected'
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    defaults = {"create": True, "read": True, "update": True, "delete": True}
    result = {}
    for row in rows:
        provider_key = row["provider_key"]
        metadata = row.get("metadata") or {}
        perms = metadata.get("permissions")
        if perms is None:
            result[provider_key] = defaults.copy()
        else:
            result[provider_key] = {
                "create": perms.get("create", False),
                "read": perms.get("read", False),
                "update": perms.get("update", False),
                "delete": perms.get("delete", False),
            }
    return result


def update_tool_permission(
    user_id: str, provider_key: str, crud_type: str, enabled: bool
) -> None:
    """Add or remove a single CRUD permission from the array."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT metadata
            FROM public.user_connectors
            WHERE user_id = %s AND provider_key = %s
            """,
            (user_id, provider_key),
        )
        row = cur.fetchone()
        if not row:
            return

        metadata = row.get("metadata") or {}
        perms = metadata.get("permissions", {"create": True, "read": True, "update": True, "delete": False})
        
        perms[crud_type] = enabled
        
        import json
        cur.execute(
            """
            UPDATE public.user_connectors
            SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{permissions}', %s::jsonb),
                updated_at = now()
            WHERE user_id = %s AND provider_key = %s
            """,
            (json.dumps(perms), user_id, provider_key),
        )


def init_default_permissions(user_id: str, provider_key: str) -> None:
    """Seed default CRUD permissions after a successful OAuth connection."""
    import json
    defaults = {"create": True, "read": True, "update": True, "delete": False}
    with get_dict_cursor() as cur:
        cur.execute(
            """
            UPDATE public.user_connectors
            SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{permissions}', %s::jsonb)
            WHERE user_id = %s AND provider_key = %s
            """,
            (json.dumps(defaults), user_id, provider_key),
        )
