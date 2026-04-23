-- Agent-scoped chat core schema (Task 1)

CREATE TABLE IF NOT EXISTS public.agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('default', 'custom')),
    name TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id, user_id)
);

CREATE TABLE IF NOT EXISTS public.agent_sessions (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE,
    agent_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agent_sessions_agent_owner_fkey
        FOREIGN KEY (agent_id, user_id)
        REFERENCES public.agents(id, user_id)
        ON DELETE CASCADE,
    UNIQUE (id, user_id, agent_id)
);

CREATE TABLE IF NOT EXISTS public.agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agent_messages_session_owner_fkey
        FOREIGN KEY (session_id, user_id, agent_id)
        REFERENCES public.agent_sessions(id, user_id, agent_id)
        ON DELETE CASCADE,
    UNIQUE (session_id, turn_index)
);

CREATE TABLE IF NOT EXISTS public.chat_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    window_index INTEGER NOT NULL,
    summary_text TEXT,
    extracted_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL CHECK (status IN ('pending', 'done', 'pending_retry', 'failed_terminal')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chat_summaries_session_owner_fkey
        FOREIGN KEY (session_id, user_id, agent_id)
        REFERENCES public.agent_sessions(id, user_id, agent_id)
        ON DELETE CASCADE,
    UNIQUE (user_id, agent_id, session_id, window_index)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_one_default_per_user
ON public.agents (user_id)
WHERE kind = 'default';

CREATE INDEX IF NOT EXISTS idx_agent_sessions_user_agent_updated_at
ON public.agent_sessions (user_id, agent_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_messages_session_created_at
ON public.agent_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_agent_messages_user_agent_session_turn
ON public.agent_messages (user_id, agent_id, session_id, turn_index);

CREATE INDEX IF NOT EXISTS idx_chat_summaries_session_window
ON public.chat_summaries (session_id, window_index);

CREATE INDEX IF NOT EXISTS idx_chat_summaries_status_updated_at
ON public.chat_summaries (status, updated_at);
