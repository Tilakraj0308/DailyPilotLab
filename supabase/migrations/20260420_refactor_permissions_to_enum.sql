-- Refactor tool permissions to use a single row with an array of ENUM values
-- Date: 2026-04-20

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tool_crud_type') THEN
        CREATE TYPE public.tool_crud_type AS ENUM ('create', 'read', 'update', 'delete');
    END IF;
END
$$;

-- Create the new table structure
CREATE TABLE IF NOT EXISTS public.connector_tool_permissions_new (
    id            SERIAL PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider_key  TEXT NOT NULL,
    allowed_cruds public.tool_crud_type[] NOT NULL DEFAULT '{}',
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, provider_key)
);

-- Migrate existing data if the old table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'connector_tool_permissions' AND table_schema = 'public') THEN
        INSERT INTO public.connector_tool_permissions_new (user_id, provider_key, allowed_cruds)
        SELECT user_id, provider_key, array_agg(crud_type::public.tool_crud_type)
        FROM public.connector_tool_permissions
        WHERE enabled = true
        GROUP BY user_id, provider_key
        ON CONFLICT (user_id, provider_key) DO UPDATE
        SET allowed_cruds = EXCLUDED.allowed_cruds;
    END IF;
END
$$;

-- Swap the tables
DROP TABLE IF EXISTS public.connector_tool_permissions;
ALTER TABLE public.connector_tool_permissions_new RENAME TO connector_tool_permissions;

-- Re-enable RLS
ALTER TABLE public.connector_tool_permissions ENABLE ROW LEVEL SECURITY;

-- Note: Policies are dropped with the table, so we must recreate them
DROP POLICY IF EXISTS "Users can manage their own tool permissions" ON public.connector_tool_permissions;
CREATE POLICY "Users can manage their own tool permissions"
    ON public.connector_tool_permissions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
