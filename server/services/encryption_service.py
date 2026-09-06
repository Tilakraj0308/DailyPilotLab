import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

class EncryptionService:
    @staticmethod
    def encrypt_data(plaintext: str, key: bytes) -> tuple[str, str]:
        """
        Encrypts a plaintext string using AES-GCM with the provided data key.
        Returns base64 encoded strings of (ciphertext, nonce).
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        
        return base64.b64encode(ciphertext).decode('utf-8'), base64.b64encode(nonce).decode('utf-8')

    @staticmethod
    def decrypt_data(ciphertext_b64: str, nonce_b64: str, key: bytes) -> str:
        """
        Decrypts base64 encoded ciphertext and nonce using AES-GCM with the provided data key.
        """
        aesgcm = AESGCM(key)
        ciphertext = base64.b64decode(ciphertext_b64.encode('utf-8'))
        nonce = base64.b64decode(nonce_b64.encode('utf-8'))
        
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode('utf-8')

encryption_service = EncryptionService()
