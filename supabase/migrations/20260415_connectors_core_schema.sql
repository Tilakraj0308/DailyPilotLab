-- ==========================================================================
-- Connector Core Schema (Canonical)
-- All provider integrations, OAuth state, tokens, permissions, history, resources.
-- This is the single source of truth for the connectors subsystem.
-- ==========================================================================

-- ─── ENUM: connector_status ────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connector_status') THEN
        CREATE TYPE public.connector_status AS ENUM (
            'disconnected',
            'connecting',
            'connected',
            'error',
            'reauth_required'
        );
    END IF;
END
$$;

-- ─── ENUM: tool_crud_type ──────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tool_crud_type') THEN
        CREATE TYPE public.tool_crud_type AS ENUM ('create', 'read', 'update', 'delete');
    END IF;
END
$$;

-- ─── TABLE: connector_providers ────────────────────────────────────────────
-- Master list of registered integration providers.

CREATE TABLE IF NOT EXISTS public.connector_providers (
    provider_key  TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.connector_providers (provider_key, display_name) VALUES
    ('google_calendar', 'Google Calendar'),
    ('google_tasks',    'Google Tasks'),
    ('gmail',          'Gmail'),
    ('notion',         'Notion')
ON CONFLICT (provider_key) DO NOTHING;

-- ─── TABLE: user_connectors ────────────────────────────────────────────────
-- Per-user connection status for each provider.

CREATE TABLE IF NOT EXISTS public.user_connectors (
    id                    BIGSERIAL PRIMARY KEY,
    user_id               TEXT NOT NULL REFERENCES public.users (auth_id) ON DELETE CASCADE,
    provider_key          TEXT NOT NULL REFERENCES public.connector_providers (provider_key) ON DELETE CASCADE,
    status                public.connector_status NOT NULL DEFAULT 'disconnected',
    scopes                TEXT[] NOT NULL DEFAULT '{}',
    external_account_id   TEXT,
    provider_email        TEXT,
    error_message         TEXT,
    connected_at          TIMESTAMPTZ,
    disconnected_at       TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_connectors_user_provider_unique UNIQUE (user_id, provider_key)
);

CREATE INDEX IF NOT EXISTS idx_user_connectors_user_id ON public.user_connectors (user_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_user_connectors_updated_at'
          AND tgrelid = 'public.user_connectors'::regclass
    ) THEN
        CREATE TRIGGER update_user_connectors_updated_at
        BEFORE UPDATE ON public.user_connectors
        FOR EACH ROW
        EXECUTE FUNCTION storage.update_updated_at_column();
    END IF;
END
$$;

-- ─── TABLE: user_connector_tokens ──────────────────────────────────────────
-- Encrypted OAuth tokens (access + refresh). One row per connector.

CREATE TABLE IF NOT EXISTS public.user_connector_tokens (
    id                       BIGSERIAL PRIMARY KEY,
    user_connector_id        BIGINT NOT NULL UNIQUE REFERENCES public.user_connectors (id) ON DELETE CASCADE,
    encrypted_access_token   BYTEA NOT NULL,
    encrypted_refresh_token  BYTEA,
    token_expires_at         TIMESTAMPTZ,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── TABLE: oauth_state_sessions ──────────────────────────────────────────
-- Short-lived PKCE state for the OAuth redirect flow.

CREATE TABLE IF NOT EXISTS public.oauth_state_sessions (
    id                  BIGSERIAL PRIMARY KEY,
    state               TEXT NOT NULL UNIQUE,
    user_id             TEXT NOT NULL REFERENCES public.users (auth_id) ON DELETE CASCADE,
    provider_key        TEXT NOT NULL REFERENCES public.connector_providers (provider_key) ON DELETE CASCADE,
    code_verifier       TEXT NOT NULL,
    oauth_redirect_uri  TEXT NOT NULL,
    return_to           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_state_sessions_expires_at ON public.oauth_state_sessions (expires_at);

-- ─── TABLE: connector_tool_permissions ────────────────────────────────────
-- User-configurable allow-list of CRUD operations per provider.

CREATE TABLE IF NOT EXISTS public.connector_tool_permissions (
    id            SERIAL PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES public.users (auth_id) ON DELETE CASCADE,
    provider_key  TEXT NOT NULL,
    allowed_cruds public.tool_crud_type[] NOT NULL DEFAULT '{}',
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT connector_tool_permissions_user_provider_key UNIQUE (user_id, provider_key)
);

ALTER TABLE public.connector_tool_permissions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own tool permissions" ON public.connector_tool_permissions;
CREATE POLICY "Users can manage their own tool permissions"
    ON public.connector_tool_permissions
    FOR ALL
    USING (auth.uid()::text = user_id)
    WITH CHECK (auth.uid()::text = user_id);

-- ─── TABLE: connector_tool_history ───────────────────────────────────────
-- Audit log of every API call made by a connector tool.

CREATE TABLE IF NOT EXISTS public.connector_tool_history (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES public.users (auth_id) ON DELETE CASCADE,
    provider_key    TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    crud_type       TEXT NOT NULL,
    params          JSONB,
    result_summary  JSONB,
    ai_tool_response JSONB,
    status          TEXT NOT NULL DEFAULT 'success',
    error_message   TEXT,
    triggered_by    TEXT NOT NULL DEFAULT 'user',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.connector_tool_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own tool history" ON public.connector_tool_history;
CREATE POLICY "Users can view their own tool history"
    ON public.connector_tool_history
    FOR SELECT
    USING (auth.uid()::text = user_id);

CREATE INDEX IF NOT EXISTS idx_tool_history_user
    ON public.connector_tool_history (user_id, created_at DESC);

-- ─── TABLE: user_connector_resources ─────────────────────────────────────
-- Provider-specific resource selections (e.g. selected Google Task List).

CREATE TABLE IF NOT EXISTS public.user_connector_resources (
    id                  BIGSERIAL PRIMARY KEY,
    user_connector_id   BIGINT NOT NULL REFERENCES public.user_connectors (id) ON DELETE CASCADE,
    resource_type       TEXT NOT NULL,
    resource_id         TEXT NOT NULL,
    resource_name       TEXT,
    is_selected         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_connector_resources_unique_type UNIQUE (user_connector_id, resource_type)
);

CREATE INDEX IF NOT EXISTS idx_user_connector_resources_user_connector_id
    ON public.user_connector_resources (user_connector_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_user_connector_resources_updated_at'
          AND tgrelid = 'public.user_connector_resources'::regclass
    ) THEN
        CREATE TRIGGER update_user_connector_resources_updated_at
        BEFORE UPDATE ON public.user_connector_resources
        FOR EACH ROW
        EXECUTE FUNCTION storage.update_updated_at_column();
    END IF;
END
$$;
