from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from db.dbConnection import get_connection
from utils.auth_middleware import get_current_user
from models.users import AiSettingsIn, AiSettingsOut
from services.kms_service import kms_service
from services.encryption_service import encryption_service

router = APIRouter()

@router.get("/ai-settings", response_model=AiSettingsOut)
def get_ai_settings(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ai_provider, ai_model, encrypted_api_key FROM public.users WHERE auth_id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            
            provider, model, enc_key = row
            return AiSettingsOut(
                ai_provider=provider,
                ai_model=model,
                has_api_key=bool(enc_key)
            )

@router.post("/ai-settings", response_model=Dict[str, Any])
def update_ai_settings(settings: AiSettingsIn, payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    
    # If the user left the api_key blank, only update provider and model
    if not settings.api_key:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.users 
                    SET ai_provider = %s, ai_model = %s
                    WHERE auth_id = %s
                    """,
                    (settings.ai_provider, settings.ai_model, user_id)
                )
                conn.commit()
                return {"status": "success"}
    
    # Generate data key from KMS
    try:
        plain_key, enc_data_key = kms_service.generate_data_key()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KMS error: {e}")
        
    # Encrypt the API key
    enc_api_key, nonce = encryption_service.encrypt_data(settings.api_key, plain_key)
    
    import base64
    enc_data_key_b64 = base64.b64encode(enc_data_key).decode('utf-8')
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.users 
                SET ai_provider = %s, ai_model = %s, encrypted_api_key = %s, encrypted_data_key = %s, encryption_iv = %s
                WHERE auth_id = %s
                """,
                (settings.ai_provider, settings.ai_model, enc_api_key, enc_data_key_b64, nonce, user_id)
            )
            conn.commit()
            return {"status": "success"}

@router.delete("/ai-settings", response_model=Dict[str, Any])
def delete_ai_settings(payload: dict = Depends(get_current_user)):
    user_id = payload.get("sub", "")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.users 
                SET ai_provider = NULL, ai_model = NULL, encrypted_api_key = NULL, encrypted_data_key = NULL, encryption_iv = NULL
                WHERE auth_id = %s
                """,
                (user_id,)
            )
            conn.commit()
            return {"status": "success"}
