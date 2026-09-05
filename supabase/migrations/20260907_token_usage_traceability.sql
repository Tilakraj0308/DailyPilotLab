-- Token Usage Traceability Module Migration
-- Created: 2026-09-07

CREATE TABLE IF NOT EXISTS public.token_usage_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE,
    session_id TEXT,
    request_type VARCHAR(50) NOT NULL DEFAULT 'chat',
    model VARCHAR(100) NOT NULL DEFAULT 'gpt-4o-mini',
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    duration_ms INT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'completed',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.token_usage_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES public.token_usage_traces(id) ON DELETE CASCADE,
    step_number INT NOT NULL DEFAULT 1,
    event_type VARCHAR(50) NOT NULL DEFAULT 'llm_call',
    name VARCHAR(150) NOT NULL,
    model VARCHAR(100),
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    estimated_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    duration_ms INT NOT NULL DEFAULT 0,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices for rapid querying & timeline sorting
CREATE INDEX IF NOT EXISTS idx_token_usage_traces_user_created 
    ON public.token_usage_traces(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_token_usage_traces_session 
    ON public.token_usage_traces(session_id);

CREATE INDEX IF NOT EXISTS idx_token_usage_timeline_trace_step 
    ON public.token_usage_timeline(trace_id, step_number ASC);

-- Row Level Security (RLS)
ALTER TABLE public.token_usage_traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_usage_timeline ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can access their own token traces" ON public.token_usage_traces;
CREATE POLICY "Users can access their own token traces"
    ON public.token_usage_traces FOR ALL
    USING (user_id = auth.uid()::text);

DROP POLICY IF EXISTS "Users can access timeline for their token traces" ON public.token_usage_timeline;
CREATE POLICY "Users can access timeline for their token traces"
    ON public.token_usage_timeline FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.token_usage_traces t 
            WHERE t.id = token_usage_timeline.trace_id AND t.user_id = auth.uid()::text
        )
    );
