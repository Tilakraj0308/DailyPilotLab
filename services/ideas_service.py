

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
    
    def get_ideas_with_filter(self, filter_column: str, filter_value: Any):
        with get_dict_cursor() as cur:
            cur.execute(f"SELECT * FROM raw_idea WHERE {filter_column} = %s", (filter_value,))
            return cur.fetchall()

    def get_unassigned_ideas(self):
        with get_dict_cursor() as cur:
            cur.execute("""
                SELECT ri.* 
                FROM raw_idea ri 
                LEFT JOIN idea_topics it ON ri.id = it.idea_id 
                WHERE it.topic_id IS NULL
            """)
            return cur.fetchall()

    def add_idea_topic_relation(self, idea_id: int, topic_id: int):
        with get_dict_cursor() as cur:
            cur.execute("INSERT INTO idea_topics (idea_id, topic_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (idea_id, topic_id))

    def remove_idea_topic_relation(self, idea_id: int, topic_id: int):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM idea_topics WHERE idea_id = %s AND topic_id = %s", (idea_id, topic_id))

    def get_topics_for_idea(self, idea_id: int):
        with get_dict_cursor() as cur:
            cur.execute("SELECT topic_id FROM idea_topics WHERE idea_id = %s", (idea_id,))
            rows = cur.fetchall()
            return [row['topic_id'] for row in rows]

    def clear_idea_topics(self, idea_id: int):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM idea_topics WHERE idea_id = %s", (idea_id,))

    def create_idea(self, insert_data: Dict[str, Any]):
        # Remove fields not in raw_idea table
        # insert_data.pop('topic_ids', None)

        with get_dict_cursor() as cur:
            if not insert_data:
                cur.execute("INSERT INTO raw_idea DEFAULT VALUES RETURNING id")
            else:
                columns = list(insert_data.keys())
                values = list(insert_data.values())
                placeholders = ["%s"] * len(values)
                query = f'INSERT INTO "raw_idea" ({", ".join(columns)}) VALUES ({", ".join(placeholders)}) RETURNING id'
                cur.execute(query, tuple(values))
            return cur.fetchone()['id']

    def bulk_create_ideas(self, data_list: List[Dict[str, Any]]):
        with get_dict_cursor() as cur:
            if not data_list:
                return
            
            # Clean data
            cleaned_list = []
            for d in data_list:
                d_copy = d.copy()
                d_copy.pop('topic_ids', None)
                cleaned_list.append(d_copy)

            if not cleaned_list:
                 return

            all_columns = set()
            for d in cleaned_list:
                all_columns.update(d.keys())
            columns = sorted(list(all_columns))

            values_list = []
            for d in cleaned_list:
                row = [d.get(col) for col in columns]
                values_list.append(tuple(row))

            placeholders = ["%s"] * len(columns)
            query = f"INSERT INTO raw_idea ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            cur.executemany(query, values_list)


    def update_idea(self, update_data: Dict[str, Any]):
        if not update_data:
            return
        
        # Remove fields not in raw_idea table
        update_data.pop('topic_ids', None)
        
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
                # Clean data
                data.pop('topic_ids', None)

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

    def assign_idea_to_topic(self, threshold: float):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM assign_and_return_matches(%s);", (threshold,))
            results = cur.fetchall()
            return results