import os
from dotenv import load_dotenv
load_dotenv()
from services.kms_service import kms_service
print(f"KMS client: {kms_service.client}")
print(f"Key ID: {kms_service.kms_key_id}")
try:
    print(kms_service.generate_data_key())
except Exception as e:
    print(f"Error: {e}")
