"""
Encrypt connector OAuth tokens at rest using Fernet (symmetric).
Key is derived from CONNECTOR_ENCRYPTION_SECRET (set a long random value in production).
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _fernet() -> Fernet:
    secret = os.getenv("CONNECTOR_ENCRYPTION_SECRET", "")
    if not secret or len(secret) < 16:
        raise RuntimeError(
            "CONNECTOR_ENCRYPTION_SECRET must be set to a strong secret (16+ chars) for connector token encryption"
        )
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_token(plaintext: str | None) -> bytes:
    if plaintext is None:
        return b""
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_token(blob: bytes | None) -> str:
    if not blob:
        return ""
    return _fernet().decrypt(blob).decode("utf-8")
