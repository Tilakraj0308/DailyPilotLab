from typing import List, Dict, Any
from db.dbConnection import get_dict_cursor

class TopicsService:
    def __init__(self):
        pass

    def get_all_topics(self):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM topic")
            topics = cur.fetchall()
            return topics

    def get_topic(self, topic_id: int):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM topic WHERE id = %s", (topic_id,))
            return cur.fetchone()

    def create_topic(self, insert_data: Dict[str, Any]):
        with get_dict_cursor() as cur:
            if not insert_data:
                cur.execute("INSERT INTO topic DEFAULT VALUES")
            else:
                columns = list(insert_data.keys())
                values = list(insert_data.values())
                placeholders = ["%s"] * len(values)
                query = f'INSERT INTO topic ({", ".join(columns)}) VALUES ({", ".join(placeholders)})'
                cur.execute(query, tuple(values))

    def bulk_create_topics(self, data_list: List[Dict[str, Any]]):
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
            query = f"INSERT INTO topic ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            cur.executemany(query, values_list)

    def update_topic(self, update_data: Dict[str, Any]):
        if not update_data:
            return
        
        topic_id = update_data.pop('id')
        
        if not update_data:
             return

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())
        values.append(topic_id)

        query = f"UPDATE topic SET {', '.join(set_clauses)} WHERE id = %s"

        with get_dict_cursor() as cur:
            cur.execute(query, tuple(values))

    def bulk_update_topics(self, data_list: List[Dict[str, Any]]):
        if not data_list:
            return
        
        with get_dict_cursor() as cur:
             for data in data_list:
                topic_id = data.pop('id')
                if not data:
                    continue
                    
                set_clauses = [f"{key} = %s" for key in data.keys()]
                values = list(data.values())
                values.append(topic_id)
                
                query = f"UPDATE topic SET {', '.join(set_clauses)} WHERE id = %s"
                cur.execute(query, tuple(values))

    def delete_topic(self, topic_id: int):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM topic WHERE id = %s", (topic_id,))

    def bulk_delete_topics(self, topic_ids: List[int]):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM topic WHERE id = ANY(%s)", (topic_ids,))

    def delete_all_topics(self):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM topic")