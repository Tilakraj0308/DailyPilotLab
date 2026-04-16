-- Create connector_tool_permissions table
CREATE TABLE IF NOT EXISTS public.connector_tool_permissions (
    id            SERIAL PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider_key  TEXT NOT NULL,
    crud_type     TEXT NOT NULL CHECK (crud_type IN ('create', 'read', 'update', 'delete')),
    enabled       BOOLEAN NOT NULL DEFAULT true,
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, provider_key, crud_type)
);

-- Enable RLS for tool permissions
ALTER TABLE public.connector_tool_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own tool permissions"
    ON public.connector_tool_permissions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Create connector_tool_history table
CREATE TABLE IF NOT EXISTS public.connector_tool_history (
    id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id        UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider_key   TEXT NOT NULL,
    tool_name      TEXT NOT NULL,
    crud_type      TEXT NOT NULL,
    params         JSONB,
    result_summary JSONB,
    status         TEXT NOT NULL DEFAULT 'success',
    error_message  TEXT,
    triggered_by   TEXT NOT NULL DEFAULT 'user',
    created_at     TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS for history
ALTER TABLE public.connector_tool_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own tool history"
    ON public.connector_tool_history
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_tool_history_user 
    ON public.connector_tool_history(user_id, created_at DESC);
