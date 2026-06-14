-- Migration to add personal_state JSONB column to the public.users table

ALTER TABLE public.users 
ADD COLUMN IF NOT EXISTS personal_state JSONB DEFAULT '{}'::jsonb;
