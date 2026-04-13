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
    key_b64 = os.getenv("CONNECTOR_ENCRYPTION_KEY", os.getenv("CONNECTOR_TOKEN_ENCRYPTION_KEY", ""))
    if not key_b64:
        raise RuntimeError("CONNECTOR_ENCRYPTION_KEY or CONNECTOR_TOKEN_ENCRYPTION_KEY is not set")
    # Support both standard and urlsafe base64 variations, and fix padding if necessary
    key_b64 = key_b64.replace("-", "+").replace("_", "/")
    key_b64 += "=" * ((4 - len(key_b64) % 4) % 4)
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise RuntimeError(
            f"CONNECTOR_ENCRYPTION_KEY must decode to 32 bytes, got {len(key)} from raw string {key_b64}"
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


def create_oauth_state(user_id: int, deep_link: str = None) -> str:
    """
    Create a signed, time-limited OAuth state parameter.

    Payload: { "user_id": int, "exp": int, "sig": str, "deep_link": ... }
    Encoded as base64url JSON.
    """
    print(f"[Crypto] create_oauth_state: user_id={user_id}, deep_link={deep_link}")
    exp = int(time.time()) + _STATE_EXPIRY_SECONDS
    message = f"{user_id}|{exp}"
    if deep_link:
        message += f"|{deep_link}"
    print(f"[Crypto] Message to sign: {message}")
    sig = _compute_hmac(message)
    print(f"[Crypto] HMAC signature: {sig}")

    payload = {"user_id": user_id, "exp": exp, "sig": sig}
    if deep_link:
        payload["deep_link"] = deep_link
    payload_json = json.dumps(payload, separators=(",", ":"))
    print(f"[Crypto] Payload JSON: {payload_json}")

    state = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii")
    print(f"[Crypto] Final state: {state}")
    return state


def verify_oauth_state(state: str) -> tuple[int, str | None]:
    """
    Verify an OAuth state parameter and return the (user_id, deep_link).

    Raises:
        ValueError: if the state is invalid, expired, or tampered with.
    """
    print(f"[Crypto] verify_oauth_state: state={state[:50]}...")
    try:
        payload_json = base64.urlsafe_b64decode(state.encode("ascii"))
        payload = json.loads(payload_json)
        print(f"[Crypto] Decoded payload: {payload}")
    except Exception as e:
        print(f"[Crypto] ERROR decoding state: {e}")
        raise ValueError(f"Malformed state parameter: {e}")

    user_id = payload.get("user_id")
    exp = payload.get("exp")
    sig = payload.get("sig")
    deep_link = payload.get("deep_link")
    
    print(f"[Crypto] user_id={user_id}, exp={exp}, sig={sig}, deep_link={deep_link}")

    if not all([user_id, exp, sig]):
        print(f"[Crypto] ERROR: Incomplete state payload")
        raise ValueError("Incomplete state payload")

    # Check expiry
    if time.time() > exp:
        print(f"[Crypto] ERROR: State has expired. Current time: {time.time()}, exp: {exp}")
        raise ValueError("State has expired")

    # Recompute HMAC and compare (constant-time)
    message = f"{user_id}|{exp}"
    if deep_link:
        message += f"|{deep_link}"
    print(f"[Crypto] Message to verify: {message}")
    expected_sig = _compute_hmac(message)
    print(f"[Crypto] Expected sig: {expected_sig}, got: {sig}")
    if not hmac.compare_digest(sig, expected_sig):
        print(f"[Crypto] ERROR: State signature mismatch")
        raise ValueError("State signature mismatch")

    print(f"[Crypto] State verified successfully. user_id={user_id}, deep_link={deep_link}")
    return int(user_id), deep_link
