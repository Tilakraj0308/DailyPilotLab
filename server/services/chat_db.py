import os
from db.dbConnection import get_dict_cursor

def save_message(user_id: str, role: str, content: str):
    """Save a chat message to the database for a user."""
    with get_dict_cursor() as cur:
        cur.execute(
            "INSERT INTO public.chat_messages (user_id, role, content) VALUES (%s, %s, %s)",
            (user_id, role, content)
        )

def load_history(user_id: str, limit: int = 15, offset: int = 0) -> list[dict]:
    """Load chronologically ordered message history for a user.
       Since we get messages paginated from newest to oldest for an inverted list,
       we fetch DESC and then reverse or just return DESC and let UI handle.
       Wait, frontend expects it DESC (newest first) for inverted FlatList.
    """
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT role, content, created_at 
            FROM public.chat_messages 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset)
        )
        return cur.fetchall()

def fetch_unprocessed_messages(user_id: str):
    """Fetch all messages for a user that haven't been processed for ideas. 
       Ordered sequentially to simulate conversation flow."""
    with get_dict_cursor() as cur:
        cur.execute(
            """
            SELECT id, role, content, created_at 
            FROM public.chat_messages 
            WHERE user_id = %s AND processed_for_ideas = false
            ORDER BY created_at ASC
            """,
            (user_id,)
        )
        return cur.fetchall()

def mark_messages_processed(message_ids: list[str]):
    """Mark a list of messages as processed for ideas."""
    if not message_ids:
        return
    with get_dict_cursor() as cur:
        cur.execute(
            "UPDATE public.chat_messages SET processed_for_ideas = true WHERE id = ANY(%s::uuid[])",
            (message_ids,)
        )

