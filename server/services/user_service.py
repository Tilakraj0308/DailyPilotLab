from db.dbConnection import get_dict_cursor, get_connection
import json

def get_personal_state(user_id: str) -> dict:
    with get_dict_cursor() as cur:
        cur.execute("SELECT personal_state FROM public.users WHERE auth_id = %s", (user_id,))
        row = cur.fetchone()
        if row and row['personal_state']:
            return row['personal_state']
    return {}

def update_personal_state_db(user_id: str, new_state: dict):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.users SET personal_state = %s WHERE auth_id = %s",
                (json.dumps(new_state), user_id)
            )
        conn.commit()
