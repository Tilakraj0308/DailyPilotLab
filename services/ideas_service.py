

from typing import List, Dict, Any
from models.ideas import IdeaCreate, IdeaUpdate, IdeaOut
from db.dbConnection import get_connection
from utils.openaiEmbeddings import get_embeddings

class IdeaService:
    def __init__(self):
        pass

    async def create_idea(self, idea: IdeaCreate):
        insert_data = idea.model_dump(exclude_unset=True)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                if not insert_data:
                    cur.execute("INSERT INTO ideas DEFAULT VALUES")
                else:
                    if not idea.embeddings and idea.content != "":
                        embeddings = await get_embeddings(idea.content)
                        insert_data["embeddings"] = embeddings[0].embedding
                    columns = list(insert_data.keys())
                    values = list(insert_data.values())
                    placeholders = ["%s"] * len(values)
                    # print(insert_data)
                    query = f"INSERT INTO ideas ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    cur.execute(query, tuple(values))
                
                conn.commit()

    async def bulk_create_ideas(self, ideas: List[IdeaCreate]):
        if not ideas:
            return

        texts_to_embed = []
        idea_indices_to_embed = []

        for i, idea in enumerate(ideas):
            if not idea.embeddings and idea.content != "":
                texts_to_embed.append(idea.content)
                idea_indices_to_embed.append(i)

        if texts_to_embed:
            embeddings_data = await get_embeddings(texts_to_embed)
            for idx, embedding_obj in zip(idea_indices_to_embed, embeddings_data):
                ideas[idx].embeddings = embedding_obj.embedding

        with get_connection() as conn:
            with conn.cursor() as cur:
                data_list = [idea.model_dump(exclude_unset=True) for idea in ideas]
                
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
                query = f"INSERT INTO ideas ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                
                cur.executemany(query, values_list)
                conn.commit()

    def get_idea(self, idea_id: int):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ideas WHERE id = %s", (idea_id,))
                return cur.fetchone()

    async def get_all_ideas(self):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ideas")
                return cur.fetchall()

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

    def bulk_delete_ideas(self, idea_ids: List[int]):
        if not idea_ids:
            return
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ideas WHERE id = ANY(%s)", (idea_ids,))
                conn.commit()