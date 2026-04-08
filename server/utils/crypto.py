"""
Cryptographic utilities for connector token management.

Provides:
- AES-256-GCM encryption/decryption for OAuth tokens at rest
- HMAC-SHA256 signing/verification for OAuth state parameters

All operations use CONNECTOR_ENCRYPTION_KEY from environment.
"""

import os
import json
import time
import hmac
import hashlib
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Key Management
# ---------------------------------------------------------------------------

def _get_encryption_key() -> bytes:
    """Load the 32-byte AES key from environment (base64-encoded)."""
    key_b64 = os.getenv("CONNECTOR_ENCRYPTION_KEY", "")
    if not key_b64:
        raise RuntimeError("CONNECTOR_ENCRYPTION_KEY is not set")
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise RuntimeError(
            f"CONNECTOR_ENCRYPTION_KEY must decode to 32 bytes, got {len(key)}"
        )
    return key


# ---------------------------------------------------------------------------
# Token Encryption (AES-256-GCM)
# ---------------------------------------------------------------------------

def encrypt_tokens(
    access_token: str, refresh_token: str
) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt access and refresh tokens using AES-256-GCM.

    Returns:
        (access_token_enc, refresh_token_enc, nonce)

    Both tokens share the same nonce because they are always
    stored/retrieved as a pair and the nonce is unique per upsert.
    """
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM

    access_enc = aesgcm.encrypt(nonce, access_token.encode("utf-8"), None)
    refresh_enc = aesgcm.encrypt(nonce, refresh_token.encode("utf-8"), None)

    return access_enc, refresh_enc, nonce


def decrypt_tokens(
    access_enc: bytes, refresh_enc: bytes, nonce: bytes
) -> tuple[str, str]:
    """
    Decrypt access and refresh tokens.

    Raises:
        cryptography.exceptions.InvalidTag: if the data is tampered with.
        RuntimeError: if the key is misconfigured.
    """
    key = _get_encryption_key()
    aesgcm = AESGCM(key)

    access_token = aesgcm.decrypt(nonce, access_enc, None).decode("utf-8")
    refresh_token = aesgcm.decrypt(nonce, refresh_enc, None).decode("utf-8")

    return access_token, refresh_token


def encrypt_single_token(token: str, nonce: bytes) -> bytes:
    """
    Encrypt a single token with an existing nonce.
    Used when refreshing only the access token.
    """
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    return aesgcm.encrypt(nonce, token.encode("utf-8"), None)


# ---------------------------------------------------------------------------
# OAuth State Signing (HMAC-SHA256)
# ---------------------------------------------------------------------------

_STATE_EXPIRY_SECONDS = 600  # 10 minutes


def _compute_hmac(message: str) -> str:
    """Compute HMAC-SHA256 of a message using the encryption key."""
    key = _get_encryption_key()
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def create_oauth_state(user_id: int) -> str:
    """
    Create a signed, time-limited OAuth state parameter.

    Payload: { "user_id": int, "exp": int, "sig": str }
    Encoded as base64url JSON.
    """
    exp = int(time.time()) + _STATE_EXPIRY_SECONDS
    message = f"{user_id}|{exp}"
    sig = _compute_hmac(message)

    payload = {"user_id": user_id, "exp": exp, "sig": sig}
    payload_json = json.dumps(payload, separators=(",", ":"))

    return base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii")


def verify_oauth_state(state: str) -> int:
    """
    Verify an OAuth state parameter and return the user_id.

    Raises:
        ValueError: if the state is invalid, expired, or tampered with.
    """
    try:
        payload_json = base64.urlsafe_b64decode(state.encode("ascii"))
        payload = json.loads(payload_json)
    except Exception as e:
        raise ValueError(f"Malformed state parameter: {e}")

    user_id = payload.get("user_id")
    exp = payload.get("exp")
    sig = payload.get("sig")

    if not all([user_id, exp, sig]):
        raise ValueError("Incomplete state payload")

    # Check expiry
    if time.time() > exp:
        raise ValueError("State has expired")

    # Recompute HMAC and compare (constant-time)
    expected_sig = _compute_hmac(f"{user_id}|{exp}")
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("State signature mismatch")

    return int(user_id)
