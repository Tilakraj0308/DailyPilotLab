-- Agent-scoped chat (if not already present) + generic background job queue.
-- Safe to run on fresh DBs; uses IF NOT EXISTS for relations.

-- -------------------------------------------------------------------------
-- Agents (one default agent per user enforced by partial unique index)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('default', 'custom')),
  name text NOT NULL,
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agents_one_default_per_user
  ON public.agents (user_id)
  WHERE (kind = 'default');

-- -------------------------------------------------------------------------
-- Agent sessions and messages
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent_sessions (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  agent_id uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id, user_id, agent_id)
);

CREATE TABLE IF NOT EXISTS public.agent_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES public.agent_sessions(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  agent_id uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('user', 'assistant')),
  content text NOT NULL,
  turn_index integer NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (session_id, turn_index)
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_session_turn
  ON public.agent_messages (session_id, turn_index);

-- -------------------------------------------------------------------------
-- Chat summaries (domain rows; worker fills summary_text / extracted_payload)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chat_summaries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  agent_id uuid NOT NULL REFERENCES public.agents(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES public.agent_sessions(id) ON DELETE CASCADE,
  window_index integer NOT NULL,
  summary_text text,
  extracted_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL CHECK (status IN ('pending', 'done', 'pending_retry', 'failed_terminal')),
  retry_count integer NOT NULL DEFAULT 0,
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, agent_id, session_id, window_index)
);

CREATE INDEX IF NOT EXISTS idx_chat_summaries_status
  ON public.chat_summaries (status, updated_at);

-- -------------------------------------------------------------------------
-- Generic background jobs (queue)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.background_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL CHECK (status IN (
    'pending',
    'in_progress',
    'retry_scheduled',
    'done',
    'failed_terminal'
  )),
  priority integer NOT NULL DEFAULT 100,
  run_at timestamptz NOT NULL DEFAULT now(),
  attempt_count integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 5,
  lease_until timestamptz,
  idempotency_key text NOT NULL,
  last_error text,
  result jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_background_jobs_idempotency UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_background_jobs_claim
  ON public.background_jobs (status, run_at, priority, created_at);

CREATE INDEX IF NOT EXISTS idx_background_jobs_lease
  ON public.background_jobs (status, lease_until)
  WHERE status = 'in_progress';

-- Optional column for older chat_summaries installs
ALTER TABLE public.chat_summaries
  ADD COLUMN IF NOT EXISTS error_message text;
