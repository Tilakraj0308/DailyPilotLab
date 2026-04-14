-- Connector foundation: providers, per-user connections, encrypted tokens, OAuth state

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

CREATE TABLE IF NOT EXISTS public.connector_providers (
    provider_key  TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.connector_providers (provider_key, display_name)
VALUES ('google_calendar', 'Google Calendar')
ON CONFLICT (provider_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.user_connectors (
    id                BIGSERIAL PRIMARY KEY,
    user_id           TEXT NOT NULL REFERENCES public.users (auth_id) ON DELETE CASCADE,
    provider_key      TEXT NOT NULL REFERENCES public.connector_providers (provider_key) ON DELETE CASCADE,
    status            public.connector_status NOT NULL DEFAULT 'disconnected',
    scopes            TEXT[] NOT NULL DEFAULT '{}',
    external_account_id TEXT,
    provider_email    TEXT,
    error_message     TEXT,
    connected_at      TIMESTAMPTZ,
    disconnected_at   TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_connectors_user_provider_unique UNIQUE (user_id, provider_key)
);

CREATE INDEX IF NOT EXISTS idx_user_connectors_user_id ON public.user_connectors (user_id);

CREATE TABLE IF NOT EXISTS public.user_connector_tokens (
    id                   BIGSERIAL PRIMARY KEY,
    user_connector_id    BIGINT NOT NULL UNIQUE REFERENCES public.user_connectors (id) ON DELETE CASCADE,
    encrypted_access_token  BYTEA NOT NULL,
    encrypted_refresh_token BYTEA,
    token_expires_at     TIMESTAMPTZ,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.oauth_state_sessions (
    id              BIGSERIAL PRIMARY KEY,
    state           TEXT NOT NULL UNIQUE,
    user_id         TEXT NOT NULL,
    provider_key    TEXT NOT NULL REFERENCES public.connector_providers (provider_key) ON DELETE CASCADE,
    code_verifier   TEXT NOT NULL,
    oauth_redirect_uri TEXT NOT NULL,
    return_to       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_state_sessions_expires_at ON public.oauth_state_sessions (expires_at);

-- Keep updated_at current on user_connectors
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
