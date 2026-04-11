

from typing import List, Dict, Any
from psycopg2.extras import execute_values
from db.dbConnection import get_dict_cursor

class IdeaService:
    def __init__(self):
        pass

    def get_all_ideas(self, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM raw_idea WHERE user_id = %s", (user_id,))
            ideas = cur.fetchall()
            return ideas

    def get_idea(self, idea_id: int, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM raw_idea WHERE id = %s AND user_id = %s", (idea_id, user_id))
            return cur.fetchone()
    
    def get_ideas_with_filter(self, filter_column: str, filter_value: Any, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute(f"SELECT * FROM raw_idea WHERE {filter_column} = %s AND user_id = %s", (filter_value, user_id))
            return cur.fetchall()
    
    def get_ideas_count(self, user_id: str, filter_column: str = None, filter_value: Any = None) -> int:
        with get_dict_cursor() as cur:
            q = f"SELECT COUNT(*) AS total_count FROM raw_idea WHERE user_id = %s"
            if filter_column:
                q = f"{q} AND {filter_column} = %s"
                cur.execute(q, (user_id, filter_value))
                data = cur.fetchall()
                return data[0]["total_count"]
            cur.execute(q, (user_id,))
            data = cur.fetchall()
            return data[0]["total_count"]

    def get_unassigned_ideas(self, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("""
                SELECT ri.id, ri.content
                FROM raw_idea ri 
                LEFT JOIN idea_topics it ON ri.id = it.idea_id 
                WHERE ri.user_id = %s AND it.topic_id IS NULL
            """, (user_id,))
            return cur.fetchall()

    def add_idea_topic_relation(self, idea_id: int, topic_id: int):
        with get_dict_cursor() as cur:
            cur.execute("INSERT INTO idea_topics (idea_id, topic_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (idea_id, topic_id))

    def remove_idea_topic_relation(self, idea_id: int=None, topic_id: int=None):
        query = "DELETE FROM idea_topics WHERE"
        values = ()
        if idea_id is not None:
            query += " idea_id = %s"
            values += (idea_id,)
        if topic_id is not None:
            query += " topic_id = %s"
            values += (topic_id,)
        with get_dict_cursor() as cur:
            cur.execute(query, values)

    def get_topics_for_idea(self, idea_id: int):
        with get_dict_cursor() as cur:
            cur.execute("SELECT topic_id FROM idea_topics WHERE idea_id = %s", (idea_id,))
            rows = cur.fetchall()
            return [row['topic_id'] for row in rows]

    # def clear_idea_topics(self, idea_id: int):
    #     with get_dict_cursor() as cur:
    #         cur.execute("DELETE FROM idea_topics WHERE idea_id = %s", (idea_id,))

    def create_idea(self, insert_data: Dict[str, Any], user_id: str):
        # Remove fields not in raw_idea table
        # insert_data.pop('topic_ids', None)

        with get_dict_cursor() as cur:
            if not insert_data:
                cur.execute("INSERT INTO raw_idea (user_id) VALUES (%s) RETURNING id", (user_id,))
            else:
                insert_data['user_id'] = user_id
                columns = list(insert_data.keys())
                values = list(insert_data.values())
                placeholders = ["%s"] * len(values)
                query = f'INSERT INTO "raw_idea" ({", ".join(columns)}) VALUES ({", ".join(placeholders)}) RETURNING id'
                cur.execute(query, tuple(values))
            return cur.fetchone()['id']

    def bulk_create_ideas(self, data_list: List[Dict[str, Any]], user_id: str):
        with get_dict_cursor() as cur:
            if not data_list:
                return
            
            for d in data_list:
                d['user_id'] = user_id

            columns = list(data_list[0].keys())

            values_list = [tuple(d[col] for col in columns) for d in data_list]
            query = f"INSERT INTO raw_idea ({', '.join(columns)}) VALUES %s"
            # cur.executemany(query, values_list)
            execute_values(cur, query, values_list)


    def update_idea(self, update_data: Dict[str, Any], user_id: str):
        if not update_data:
            return
        
        # Remove fields not in raw_idea table
        update_data.pop('topic_ids', None)
        
        idea_id = update_data.pop('id', None)
        if idea_id is None:
            return
        
        if not update_data:
             return

        set_clauses = [f"{key} = %s" for key in update_data.keys()]
        values = list(update_data.values())
        values.extend([idea_id, user_id])

        query = f"UPDATE raw_idea SET {', '.join(set_clauses)} WHERE id = %s AND user_id = %s"

        with get_dict_cursor() as cur:
            cur.execute(query, tuple(values))

    # def bulk_update_ideas(self, data_list: List[Dict[str, Any]]):
    #     if not data_list:
    #         return
        
    #     with get_dict_cursor() as cur:
    #          for data in data_list:
    #             # Clean data
    #             data.pop('topic_ids', None)

    #             idea_id = data.pop('id', None)
    #             if idea_id is None:
    #                 continue
    #             if not data:
    #                 continue
                    
    #             set_clauses = [f"{key} = %s" for key in data.keys()]
    #             values = list(data.values())
    #             values.append(idea_id)
                
    #             query = f"UPDATE raw_idea SET {', '.join(set_clauses)} WHERE id = %s"
    #             cur.execute(query, tuple(values))

    def delete_idea(self, idea_id: int, user_id: str):
        # Topics reference would be deleted using cascade option set.
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM raw_idea WHERE id = %s AND user_id = %s", (idea_id, user_id))

    def delete_raw_ideas(self, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM raw_idea WHERE raw = TRUE AND user_id = %s", (user_id,))

    def bulk_delete_ideas(self, idea_ids: List[int], user_id: str):
        # Topics reference would be deleted using cascade option set.
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM raw_idea WHERE id = ANY(%s) AND user_id = %s", (idea_ids, user_id))

    def delete_all_ideas(self, user_id: str):
        # Topics reference would be deleted using cascade option set.
        with get_dict_cursor() as cur:
            cur.execute("DELETE FROM raw_idea WHERE user_id = %s", (user_id,))

    def assign_idea_to_topic(self, threshold: float, user_id: str):
        with get_dict_cursor() as cur:
            cur.execute("SELECT * FROM assign_and_return_matches(%s, %s);", (threshold, user_id))
            results = cur.fetchall()
            return results

    def search_topics_and_ideas(
        self, 
        query_embedding: list, 
        user_id: str,
        n_topics: int = 5, 
        k_ideas: int = 3,
        topic_similarity_threshold: float = 0.70,  # e.g., 70% match for topics
        idea_similarity_threshold: float = 0.75    # e.g., 75% match for specific ideas
    ) -> list:
        
        # 1. Convert human-readable similarity thresholds to database-friendly distance thresholds
        topic_dist_thresh = 1.0 - topic_similarity_threshold
        idea_dist_thresh = 1.0 - idea_similarity_threshold

        with get_dict_cursor() as cur:
            cur.execute("""
                WITH top_topics AS (
                    SELECT id, title, summary,
                        (1 - (summary_embedding <=> %(query)s::vector)) AS topic_similarity
                    FROM topic
                    WHERE is_archived = false AND user_id = %(user_id)s
                    AND (summary_embedding <=> %(query)s::vector) <= %(topic_thresh)s
                    ORDER BY summary_embedding <=> %(query)s::vector
                    LIMIT %(n_topics)s
                )
                SELECT t.id AS topic_id, t.title, t.summary, t.topic_similarity,
                    r.idea_id, r.content AS idea_content, r.idea_similarity
                FROM top_topics t
                JOIN LATERAL (
                    SELECT r.id AS idea_id, r.content, 
                        (1 - (r.embeddings <=> %(query)s::vector)) AS idea_similarity
                    FROM idea_topics it
                    JOIN raw_idea r ON r.id = it.idea_id
                    WHERE it.topic_id = t.id AND r.user_id = %(user_id)s
                    AND r.embeddings IS NOT NULL
                    AND (r.embeddings <=> %(query)s::vector) <= %(idea_thresh)s
                    ORDER BY r.embeddings <=> %(query)s::vector
                    LIMIT %(k_ideas)s
                ) r ON true
            """, {
                "query": query_embedding,
                "n_topics": n_topics,
                "k_ideas": k_ideas,
                "topic_thresh": topic_dist_thresh,
                "idea_thresh": idea_dist_thresh,
                "user_id": user_id
            }) 

            rows = cur.fetchall()
            
            return rows