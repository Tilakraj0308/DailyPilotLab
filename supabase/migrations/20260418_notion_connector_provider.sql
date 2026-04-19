-- Seed Notion as a connector provider (OAuth + tools registered in app code)

INSERT INTO public.connector_providers (provider_key, display_name)
VALUES ('notion', 'Notion')
ON CONFLICT (provider_key) DO NOTHING;
