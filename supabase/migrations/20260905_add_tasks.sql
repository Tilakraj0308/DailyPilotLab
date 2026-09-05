-- Migration: add_tasks
-- Adds the tasks table with status and priority enums.
-- Uses storage.update_updated_at_column() consistent with all other tables in this project.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_status') THEN
        CREATE TYPE public.task_status AS ENUM ('todo', 'in_progress', 'done', 'cancelled');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_priority') THEN
        CREATE TYPE public.task_priority AS ENUM ('low', 'medium', 'high', 'urgent');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.tasks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    description  TEXT,
    status       public.task_status   NOT NULL DEFAULT 'todo',
    priority     public.task_priority NOT NULL DEFAULT 'medium',
    due_date     TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-update updated_at using the same function as all other tables
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_tasks_updated_at'
          AND tgrelid = 'public.tasks'::regclass
    ) THEN
        CREATE TRIGGER update_tasks_updated_at
            BEFORE UPDATE ON public.tasks
            FOR EACH ROW EXECUTE FUNCTION storage.update_updated_at_column();
    END IF;
END
$$;

-- Fast per-user list fetches
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON public.tasks(user_id);

-- RLS: users can only see/modify their own tasks
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tasks_user_isolation ON public.tasks;
CREATE POLICY tasks_user_isolation ON public.tasks
    FOR ALL
    USING (user_id = auth.uid()::TEXT)
    WITH CHECK (user_id = auth.uid()::TEXT);
