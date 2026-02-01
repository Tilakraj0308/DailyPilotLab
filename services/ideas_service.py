

from typing import List, Dict, Any
from db.dbConnection import get_dict_cursor

class IdeaService:
    def __init__(self):
        pass

    def get_all_ideas(self):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM raw_idea")
            ideas = cur.fetchall()
            print("THIS IS IDEAS")
            print(ideas)
            return ideas

    def get_idea(self, idea_id: int):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM raw_idea WHERE id = %s", (idea_id,))
            return cur.fetchone()

    def create_idea(self, insert_data: Dict[str, Any]):
        
        with get_dict_cursor() as cur:
            if not insert_data:
                cur.execute("INSERT INTO raw_idea DEFAULT VALUES")
            else:
                columns = list(insert_data.keys())
                values = list(insert_data.values())
                placeholders = ["%s"] * len(values)
                query = f'INSERT INTO "raw_idea" ({', '.join(columns)}) VALUES ({', '.join(placeholders)})'
                cur.execute(query, tuple(values))

    def bulk_create_ideas(self, data_list: List[Dict[str, Any]]):
        with get_dict_cursor() as cur:
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
            query = f"INSERT INTO raw_idea ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            cur.executemany(query, values_list)


    def update_idea(self, update_data: Dict[str, Any]):
        # update_data = idea.model_dump(exclude_unset=True)
        if not update_data:
            return
        
        idea_id = update_data.pop('id')
        
        if not update_data:
             return

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())
        values.append(idea_id)

        query = f"UPDATE raw_idea SET {', '.join(set_clauses)} WHERE id = %s"

        with get_dict_cursor() as cur:
            cur.execute(query, tuple(values))

    def bulk_update_ideas(self, data_list: List[Dict[str, Any]]):
        if not data_list:
            return
        
        with get_dict_cursor() as cur:
             for data in data_list:
                idea_id = data.pop('id')
                if not data:
                    continue
                    
                set_clauses = [f"{key} = %s" for key in data.keys()]
                values = list(data.values())
                values.append(idea_id)
                
                query = f"UPDATE raw_idea SET {', '.join(set_clauses)} WHERE id = %s"
                cur.execute(query, tuple(values))

    def delete_idea(self, idea_id: int):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM raw_idea WHERE id = %s", (idea_id,))

    def bulk_delete_ideas(self, idea_ids: List[int]):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM raw_idea WHERE id = ANY(%s)", (idea_ids,))

    def delete_all_ideas(self):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM raw_idea")