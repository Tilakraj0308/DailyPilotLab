-- 1. Add user_id and processed_for_ideas to chat_messages
ALTER TABLE public.chat_messages ADD COLUMN user_id TEXT REFERENCES public.users(auth_id) ON DELETE CASCADE;
ALTER TABLE public.chat_messages ADD COLUMN processed_for_ideas BOOLEAN DEFAULT false;

-- 2. Delete existing table data before applying NOT NULL constraint since we are imagining no data
DELETE FROM public.chat_messages;

-- 3. Now make user_id NOT NULL and remove requirement on session_id
ALTER TABLE public.chat_messages ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE public.chat_messages ALTER COLUMN session_id DROP NOT NULL;

-- 4. Drop the foreign key constraint to session_id, the dependency column, and the table itself
ALTER TABLE public.chat_messages DROP CONSTRAINT chat_messages_session_id_fkey;
ALTER TABLE public.chat_messages DROP COLUMN session_id;
DROP TABLE public.chat_sessions CASCADE;

-- 5. Add status to raw_idea
ALTER TABLE public.raw_idea ADD COLUMN status VARCHAR(30) DEFAULT 'active';

-- Leaving the 'raw' column for backward compatibility or future use, but rely on 'status'.
