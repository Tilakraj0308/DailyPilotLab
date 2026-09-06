-- Migration to add AI Provider Settings to the users table

ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS ai_provider TEXT,
ADD COLUMN IF NOT EXISTS ai_model TEXT,
ADD COLUMN IF NOT EXISTS encrypted_api_key TEXT,
ADD COLUMN IF NOT EXISTS encrypted_data_key TEXT,
ADD COLUMN IF NOT EXISTS encryption_iv TEXT;
