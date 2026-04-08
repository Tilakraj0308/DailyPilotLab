"""
Fernet-based encryption/decryption for OAuth tokens.

Tokens stored in connector_tokens are encrypted at rest.
The key is read from the CONNECTOR_TOKEN_ENCRYPTION_KEY env var.
"""

import os
from cryptography.fernet import Fernet

_KEY = os.getenv("CONNECTOR_TOKEN_ENCRYPTION_KEY", "")


def _get_fernet() -> Fernet:
    if not _KEY:
        raise RuntimeError(
            "CONNECTOR_TOKEN_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(_KEY.encode())


def encrypt_token(plaintext: str) -> str:
    """Encrypt a plaintext token string → base64 ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a base64 ciphertext → plaintext token string."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
