import boto3
import os
from botocore.exceptions import BotoCoreError, ClientError

class KMSService:
    def __init__(self):
        # Requires AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY to be set in env
        # Or configured via AWS credentials profile.
        # KMS Key ID should be in AWS_KMS_KEY_ID
        self.kms_key_id = os.getenv("AWS_KMS_KEY_ID")
        region = os.getenv("AWS_REGION", "us-east-1")
        try:
            self.client = boto3.client('kms', region_name=region)
        except Exception as e:
            self.client = None
            print(f"Failed to initialize KMS client: {e}")

    def generate_data_key(self):
        """
        Generates a data key using KMS.
        Returns a tuple: (plaintext_key_bytes, encrypted_key_bytes)
        """
        if not self.client or not self.kms_key_id:
            raise ValueError("KMS client or KMS Key ID not configured.")
        
        try:
            response = self.client.generate_data_key(
                KeyId=self.kms_key_id,
                KeySpec='AES_256'
            )
            return response['Plaintext'], response['CiphertextBlob']
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Error generating data key: {e}")

    def decrypt_data_key(self, encrypted_key_bytes: bytes) -> bytes:
        """
        Decrypts an encrypted data key using KMS.
        """
        if not self.client:
            raise ValueError("KMS client not configured.")
            
        try:
            response = self.client.decrypt(
                CiphertextBlob=encrypted_key_bytes
            )
            return response['Plaintext']
        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Error decrypting data key: {e}")

kms_service = KMSService()
