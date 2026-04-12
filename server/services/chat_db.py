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
    """Save a chat message to the database and update session updated_at."""
    with get_dict_cursor() as cur:
        cur.execute(
            "INSERT INTO public.chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content)
        )
        cur.execute(
            "UPDATE public.chat_sessions SET updated_at = now() WHERE id = %s",
            (session_id,)
        )

def load_history(session_id: str) -> list[dict]:
    """Load chronologically ordered message history for a session."""
    with get_dict_cursor() as cur:
        cur.execute(
            "SELECT role, content FROM public.chat_messages WHERE session_id = %s ORDER BY created_at",
            (session_id,)
        )
        return cur.fetchall()

def get_user_sessions(user_id: str) -> list[dict]:
    """Fetch all chat sessions for a user, including the first message as title."""
    with get_dict_cursor() as cur:
        cur.execute(
            '''
            SELECT 
                s.id, 
                s.updated_at,
                s.created_at,
                (
                    SELECT content 
                    FROM public.chat_messages m 
                    WHERE m.session_id = s.id AND m.role = 'user' 
                    ORDER BY created_at ASC 
                    LIMIT 1
                ) as title
            FROM public.chat_sessions s
            WHERE s.user_id = %s
            ORDER BY s.updated_at DESC
            ''',
            (user_id,)
        )
        return cur.fetchall()

