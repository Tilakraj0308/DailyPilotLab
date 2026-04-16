-- Google Tasks connector: provider row + generic selected resource (task list)

INSERT INTO public.connector_providers (provider_key, display_name)
VALUES ('google_tasks', 'Google Tasks')
ON CONFLICT (provider_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.user_connector_resources (
    id                 BIGSERIAL PRIMARY KEY,
    user_connector_id  BIGINT NOT NULL REFERENCES public.user_connectors (id) ON DELETE CASCADE,
    resource_type      TEXT NOT NULL,
    resource_id        TEXT NOT NULL,
    resource_name      TEXT,
    is_selected        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
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
