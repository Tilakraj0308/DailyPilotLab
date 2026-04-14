"""
Base connector lifecycle: DB operations shared by all providers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from db.dbConnection import get_dict_cursor

logger = logging.getLogger(__name__)


def cleanup_expired_oauth_states() -> None:
    with get_dict_cursor() as cur:
        cur.execute("DELETE FROM public.oauth_state_sessions WHERE expires_at < now()")


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
    from utils.crypto_tokens import encrypt_token

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
                uc.error_message
            FROM public.connector_providers cp
            LEFT JOIN public.user_connectors uc
                ON uc.provider_key = cp.provider_key AND uc.user_id = %s
            ORDER BY cp.provider_key
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_user_connector_id(user_id: str, provider_key: str) -> int | None:
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT id FROM public.user_connectors WHERE user_id = %s AND provider_key = %s",
            (user_id, provider_key),
        )
        row = cur.fetchone()
        return int(row["id"]) if row else None


def delete_tokens_and_disconnect(user_id: str, provider_key: str) -> dict[str, Any] | None:
    """Returns decrypted refresh_token if present (for provider revoke)."""
    from utils.crypto_tokens import decrypt_token

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
