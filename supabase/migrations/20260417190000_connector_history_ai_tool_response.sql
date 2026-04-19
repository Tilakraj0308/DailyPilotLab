-- Full JSON object passed to the LLM as tool message content (matches chat_service json.dumps payload).
ALTER TABLE public.connector_tool_history
    ADD COLUMN IF NOT EXISTS ai_tool_response JSONB;
