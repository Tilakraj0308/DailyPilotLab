from db.dbConnection import get_dict_cursor, get_connection
import json
import os
import redis

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
except Exception:
    redis_client = None

def get_personal_state(user_id: str) -> dict:
    if redis_client:
        cached_state = redis_client.get(f"personal_state:{user_id}")
        if cached_state:
            try:
                return json.loads(cached_state)
            except json.JSONDecodeError:
                pass

    with get_dict_cursor() as cur:
        cur.execute("SELECT personal_state FROM public.users WHERE auth_id = %s", (user_id,))
        row = cur.fetchone()
        if row and row['personal_state']:
            if redis_client:
                redis_client.set(f"personal_state:{user_id}", json.dumps(row['personal_state']), ex=3600)
            return row['personal_state']
            
    if redis_client:
        redis_client.set(f"personal_state:{user_id}", "{}", ex=3600)
    return {}

def update_personal_state_db(user_id: str, new_state: dict):
    if redis_client:
        redis_client.set(f"personal_state:{user_id}", json.dumps(new_state), ex=3600)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.users SET personal_state = %s WHERE auth_id = %s",
                (json.dumps(new_state), user_id)
            )
        conn.commit()

def merge_personal_state(user_id: str, delta_state: dict) -> dict:
    current_state = get_personal_state(user_id)
    new_state = current_state.copy()
    new_state.update(delta_state)
    update_personal_state_db(user_id, new_state)
    return new_state
