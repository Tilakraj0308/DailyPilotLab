

from typing import List, Dict, Any
from models.ideas import IdeaCreate, IdeaUpdate, IdeaOut
from db.dbConnection import get_connection
from utils.openaiEmbeddings import get_embeddings

class IdeaService:
    def __init__(self):
        pass

    def get_all_ideas(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rawIdea")
                return cur.fetchall()

    def get_idea(self, idea_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM rawIdea WHERE id = %s", (idea_id,))
                return cur.fetchone()

    def create_idea(self, insert_data: Dict[str, Any]):
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                if not insert_data:
                    cur.execute("INSERT INTO rawIdea DEFAULT VALUES")
                else:
                    columns = list(insert_data.keys())
                    values = list(insert_data.values())
                    placeholders = ["%s"] * len(values)
                    query = f"INSERT INTO rawIdea ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    cur.execute(query, tuple(values))
                
                conn.commit()

    def bulk_create_ideas(self, data_list: List[Dict[str, Any]]):
        with get_connection() as conn:
            with conn.cursor() as cur:
                if not data_list:
                    return
                all_columns = set()
                for d in data_list:
                    all_columns.update(d.keys())
                columns = sorted(list(all_columns))

                values_list = []
                for d in data_list:
                    row = [d.get(col) for col in columns]
                    values_list.append(tuple(row))

                placeholders = ["%s"] * len(columns)
                query = f"INSERT INTO rawIdea ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                
                cur.executemany(query, values_list)
                conn.commit()


    def update_idea(self, idea_id: int, update_data: Dict[str, Any]):
        # update_data = idea.model_dump(exclude_unset=True)
        if not update_data:
            return
        
        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())
        values.append(idea_id)

        query = f"UPDATE rawIdea SET {', '.join(set_clauses)} WHERE id = %s"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                conn.commit()

    def delete_idea(self, idea_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rawIdea WHERE id = %s", (idea_id,))
                conn.commit()

    def bulk_delete_ideas(self, idea_ids: List[int]):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rawIdea WHERE id = ANY(%s)", (idea_ids,))
                conn.commit()

    def delete_all_ideas(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rawIdea")
                conn.commit()