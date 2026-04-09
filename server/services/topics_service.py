from typing import List, Dict, Any
from psycopg2.extras import execute_values
from db.dbConnection import get_dict_cursor

class TopicsService:
    def __init__(self):
        pass

    def get_all_topics(self, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM topic WHERE user_id = %s", (user_id,))
            topics = cur.fetchall()
            return topics

    def get_topic(self, topic_id: int, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM topic WHERE id = %s AND user_id = %s", (topic_id, user_id))
            return cur.fetchone()

    def create_topic(self, insert_data: Dict[str, Any], user_id: str):
        # idea_ids = insert_data.pop('idea_ids', None)
        with get_dict_cursor() as cur:
            if not insert_data:
                cur.execute("INSERT INTO topic (user_id) VALUES (%s) RETURNING id", (user_id,))
                res = cur.fetchone()
                topic_id = res['id'] if res else None
            else:
                insert_data['user_id'] = user_id
                columns = list(insert_data.keys())
                values = list(insert_data.values())
                placeholders = ["%s"] * len(values)
                query = f'INSERT INTO topic ({", ".join(columns)}) VALUES ({", ".join(placeholders)}) RETURNING id'
                cur.execute(query, tuple(values))
                res = cur.fetchone()
                topic_id = res['id'] if res else None
                
            # if topic_id and idea_ids:
            #     rows = [(idea_id, topic_id) for idea_id in idea_ids]
            #     execute_values(
            #         cur,
            #         "INSERT INTO idea_topics (idea_id, topic_id) VALUES %s ON CONFLICT DO NOTHING",
            #         rows
            #     )
                
            return topic_id

    def bulk_create_topics(self, data_list: List[Dict[str, Any]], user_id: str):
        if not data_list or len(data_list) == 0:
            return

        for d in data_list:
            d['user_id'] = user_id

        all_columns = data_list[0].keys()
        columns = list(all_columns)
        rows = [tuple(d.get(col) for col in columns) for d in data_list]

        query = f"INSERT INTO topic ({', '.join(columns)}) VALUES %s RETURNING id"

        with get_dict_cursor() as cur:
            execute_values(cur, query, rows)
            results = cur.fetchall()
            return [row['id'] for row in results]

    def update_topic(self, update_data: Dict[str, Any], user_id: str):
        if not update_data:
            return
        
        # update_data.pop('idea_ids', None)
        topic_id = update_data.pop('id', None)
        if topic_id is None:
            return
        
        if not update_data:
             return

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())
        values.extend([topic_id, user_id])

        query = f"UPDATE topic SET {', '.join(set_clauses)} WHERE id = %s AND user_id = %s"

        with get_dict_cursor() as cur:
            cur.execute(query, tuple(values))

    def bulk_update_topics(self, data_list: List[Dict[str, Any]], user_id: str):
        if not data_list:
            return

        for d in data_list:
            d['user_id'] = user_id

        # Assume all items have the same format; derive keys from the first item
        first_item = data_list[0].copy()
        first_item.pop('id', None)
        
        if not first_item:
            return
            
        keys = tuple(sorted(first_item.keys()))
        columns = ['id'] + list(keys)
        
        rows = []
        for data in data_list:
            topic_id = data.get('id')
            if topic_id is None:
                continue
            rows.append((topic_id,) + tuple(data.get(k) for k in keys))
            
        if not rows:
            return

        set_clauses = [f"{key} = c.{key}" for key in keys]
        
        query = f"""
            UPDATE topic AS t
            SET {', '.join(set_clauses)}
            FROM (VALUES %s) AS c({', '.join(columns)})
            WHERE t.id = c.id::int AND t.user_id = c.user_id
        """

        with get_dict_cursor() as cur:
            execute_values(cur, query, rows)

    def append_idea_ids(self, updates: List[Dict[str, Any]]):
        """Append idea IDs to one or more topics.

        Each item in ``updates`` must have:
            - 'id'       (int)       : the topic's database ID
            - 'idea_ids' (List[int]) : IDs to append (duplicates are ignored)
        """
        rows = []
        for u in updates:
            topic_id = u.get("id")
            idea_ids = u.get("idea_ids")
            if topic_id is not None and idea_ids:
                for idea_id in idea_ids:
                    rows.append((idea_id, topic_id))

        if not rows:
            return

        query = """
            INSERT INTO idea_topics (idea_id, topic_id)
            VALUES %s
            ON CONFLICT DO NOTHING
        """
        
        with get_dict_cursor() as cur:
            execute_values(cur, query, rows)

    def delete_topic(self, topic_id: int, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM topic WHERE id = %s AND user_id = %s", (topic_id, user_id))

    def bulk_delete_topics(self, topic_ids: List[int], user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM topic WHERE id = ANY(%s) AND user_id = %s", (topic_ids, user_id))

    def delete_all_topics(self, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM topic WHERE user_id = %s", (user_id,))

    def refresh_topic_recency(self, user_id: str):
        """
        Calls the Supabase internal function to update activity_7d, 
        activity_30d, and lifetime_size.
        """
        with get_dict_cursor() as cur:
            cur.execute("SELECT update_topic_recency_metrics(%s);", (user_id,))

    # In services/topics_service.py

    def get_high_signal_topics(self, user_id: str, recency_threshold: int = 5, dominance_threshold: int = 15):
        """
        Fetches topics that meet either the recency or dominance threshold.
        Returns only the human-readable data needed for LLM trait generation.
        """
        query = """
            SELECT 
                t.id, 
                t.title, 
                t.summary
            FROM topic t
            WHERE (t.recency_strength >= %s 
            OR t.dominance >= %s) AND t.user_id = %s
            ORDER BY t.recency_strength DESC, t.dominance DESC;
        """
        
        with get_dict_cursor() as cur:
            # Pass the thresholds into the query safely
            cur.execute(query, (recency_threshold, dominance_threshold, user_id))
            high_signal_topics = cur.fetchall()
            
            return high_signal_topics

    # In services/ideas_service.py

    def get_recent_ideas_for_topic(self, topic_id: int, user_id: str, limit: int = 3):
        """
        Fetches the most recent raw ideas linked to a specific topic
        to use as memory snippets for trait generation.
        """
        query = """
            SELECT ri.id, ri.content, ri.created_at
            FROM raw_idea ri
            JOIN idea_topics it ON ri.id = it.idea_id
            WHERE it.topic_id = %s AND ri.user_id = %s
            ORDER BY ri.created_at DESC
            LIMIT %s
        """
        with get_dict_cursor() as cur:
            cur.execute(query, (topic_id, user_id, limit))
            return cur.fetchall()