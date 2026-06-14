-- Add onboarding_completed flag to gate the first-login questionnaire.
-- personal_state column already exists (see 20260523_add_personal_state_to_users.sql).
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE;
