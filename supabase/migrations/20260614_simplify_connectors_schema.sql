-- ==========================================================================
-- Simplify Connectors Schema
-- Drops 4 normalized tables and adds token/metadata columns directly to user_connectors
-- ==========================================================================

-- 1. Drop foreign key constraints referencing connector_providers
ALTER TABLE public.user_connectors 
    DROP CONSTRAINT IF EXISTS user_connectors_provider_key_fkey;

ALTER TABLE public.oauth_state_sessions 
    DROP CONSTRAINT IF EXISTS oauth_state_sessions_provider_key_fkey;

-- Note: connector_tool_history does not have a foreign key to connector_providers.

-- 2. Add new columns to user_connectors
ALTER TABLE public.user_connectors
    ADD COLUMN IF NOT EXISTS access_token BYTEA,
    ADD COLUMN IF NOT EXISTS refresh_token BYTEA,
    ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- 3. Drop the 4 tables we are replacing
DROP TABLE IF EXISTS public.connector_tool_permissions CASCADE;
DROP TABLE IF EXISTS public.user_connector_resources CASCADE;
DROP TABLE IF EXISTS public.user_connector_tokens CASCADE;
DROP TABLE IF EXISTS public.connector_providers CASCADE;

-- 4. Clean up types if any unused (tool_crud_type is still used by frontend concept, but no longer in DB schema explicitly, wait, is tool_crud_type used anywhere else?)
-- Actually, we'll keep tool_crud_type as it might be used or referenced, but it was only used in connector_tool_permissions.
-- Let's leave the type for now to be safe.
