import os
import base64
from openai import OpenAI, AsyncOpenAI
from db.dbConnection import get_connection
from services.kms_service import kms_service
from services.encryption_service import encryption_service

class AIFactory:
    @staticmethod
    def get_user_ai_settings(user_id: str):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT ai_provider, ai_model, encrypted_api_key, encrypted_data_key, encryption_iv FROM public.users WHERE auth_id = %s",
                        (user_id,)
                    )
                    row = cur.fetchone()
                    if row and row[2] and row[3] and row[4]:
                        provider, model, enc_key, enc_data_key_b64, nonce_b64 = row
                        
                        # Decrypt the data key
                        enc_data_key = base64.b64decode(enc_data_key_b64.encode('utf-8'))
                        plain_data_key = kms_service.decrypt_data_key(enc_data_key)
                        
                        # Decrypt the API key
                        api_key = encryption_service.decrypt_data(enc_key, nonce_b64, plain_data_key)
                        
                        return {
                            "provider": provider or "openai",
                            "model": model or "gpt-4o-mini",
                            "api_key": api_key
                        }
        except Exception as e:
            print(f"Error retrieving user AI settings for {user_id}: {e}")
            
        # Fallback to default
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": os.getenv("OPENAPI")
        }
        
    @staticmethod
    def get_openai_client(user_id: str) -> OpenAI:
        settings = AIFactory.get_user_ai_settings(user_id)
        return OpenAI(api_key=settings["api_key"])
        
    @staticmethod
    def get_async_openai_client(user_id: str) -> AsyncOpenAI:
        settings = AIFactory.get_user_ai_settings(user_id)
        return AsyncOpenAI(api_key=settings["api_key"])
