-- Add tool_calls and tool_call_id to chat_messages to persist OpenAI tool execution states
-- This enables multi-turn tool calling context across chat sessions.

ALTER TABLE public.chat_messages
ADD COLUMN IF NOT EXISTS tool_calls JSONB,
ADD COLUMN IF NOT EXISTS tool_call_id TEXT;

-- Update the chat_messages_role_check constraint to support 'tool' and 'system' roles
-- This is necessary to persist OpenAI's tool execution messages in the chat history.
ALTER TABLE public.chat_messages
DROP CONSTRAINT IF EXISTS chat_messages_role_check;

ALTER TABLE public.chat_messages
ADD CONSTRAINT chat_messages_role_check CHECK (role = ANY (ARRAY['user'::text, 'assistant'::text, 'tool'::text, 'system'::text]));
