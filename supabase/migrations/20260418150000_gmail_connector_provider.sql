INSERT INTO public.connector_providers (provider_key, display_name)
VALUES ('gmail', 'Gmail')
ON CONFLICT (provider_key) DO NOTHING;
