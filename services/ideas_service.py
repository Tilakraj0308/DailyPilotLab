# from models.thoughts import IdeaCreate, IdeaUpdate
# from database.connection import get_connection

from models.ideas import IdeaCreate, IdeaUpdate, IdeaOut
from db.dbConnection import get_connection

class IdeaService:
    def __init__(self):
        pass

    def create_idea(self, idea: IdeaCreate):
        insert_data = idea.model_dump(exclude_unset=True)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                if not insert_data:
                    cur.execute("INSERT INTO ideas DEFAULT VALUES")
                else:
                    columns = list(insert_data.keys())
                    values = list(insert_data.values())
                    placeholders = ["%s"] * len(values)
                    query = f"INSERT INTO ideas ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    cur.execute(query, tuple(values))
                
                conn.commit()

    def get_idea(self, idea_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ideas WHERE id = %s", (idea_id,))
                return cur.fetchone()

    def update_idea(self, idea_id: int, idea: IdeaUpdate):
        update_data = idea.model_dump(exclude_unset=True)
        if not update_data:
            return

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())
        values.append(idea_id)

        query = f"UPDATE ideas SET {', '.join(set_clauses)} WHERE id = %s"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                conn.commit()

    def delete_idea(self, idea_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ideas WHERE id = %s", (idea_id,))
                conn.commit()