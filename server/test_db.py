from services.user_service import update_personal_state_db
import json
from db.dbConnection import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT auth_id FROM public.users LIMIT 1")
        user = cur.fetchone()
        if user:
            print(f"Found user: {user[0]}")
            cur.execute(
                """
                UPDATE public.users
                SET personal_state = %s::jsonb,
                    onboarding_completed = TRUE
                WHERE auth_id = %s
                RETURNING id
                """,
                (json.dumps({"nickname": "test"}), user[0])
            )
            print("Update result:", cur.fetchone())
            conn.commit()
        else:
            print("No users found")
