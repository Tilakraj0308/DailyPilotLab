import os
from db.dbConnection import get_dict_cursor

def get_or_create_session(session_id: str, user_id: str) -> str:
    """Ensure the chat session exists in the database."""
    with get_dict_cursor() as cur:
        cur.execute("SELECT id FROM public.chat_sessions WHERE id = %s AND user_id = %s", (session_id, user_id))
        if not cur.fetchone():
            cur.execute("INSERT INTO public.chat_sessions (id, user_id) VALUES (%s, %s)", (session_id, user_id))
    return session_id

def save_message(session_id: str, role: str, content: str):
    """Save a chat message to the database."""
    with get_dict_cursor() as cur:
        cur.execute(
            "INSERT INTO public.chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content)
        )

def load_history(session_id: str) -> list[dict]:
    """Load chronologically ordered message history for a session."""
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT role, content FROM public.chat_messages WHERE session_id = %s ORDER BY created_at",
            (session_id,)
        )
        return cur.fetchall()
