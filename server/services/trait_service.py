from db.dbConnection import get_dict_cursor
from models.traits import TraitCandidate
from typing import List

class TraitsService:
    def __init__(self, openai_client=None):
        self.openai_client = openai_client

    def get_user_traits(self, user_id: str) -> List[dict]:
        with get_dict_cursor() as cur:
            cur.execute("""
                SELECT id, trait_text, trait_type, confidence, created_at, last_evidenced_at
                FROM trait
                WHERE user_id = %s
                ORDER BY confidence DESC
            """, (user_id,))
            return cur.fetchall()

    def process_and_upsert_traits(self, new_traits: List[TraitCandidate], user_id: str):
        """
        Embeds new traits, checks for semantic duplicates, and applies EMA smoothing.
        """
        for trait in new_traits:
            embedding_response = self.openai_client.embeddings.create(
                input=trait.trait_text, 
                model="text-embedding-3-small" 
            )
            vector = embedding_response.data[0].embedding
            search_query = """
                SELECT id, confidence 
                FROM trait
                WHERE (embedding <=> %s::vector) <= 0.12 AND user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT 1
            """
            
            with get_dict_cursor() as cur:
                cur.execute(search_query, (vector, user_id, vector))
                match = cur.fetchone()
                
                if match:
                    existing_id = match['id']
                    current_conf = float(match['confidence'])
                    instant_score = trait.confidence_suggestion
                    
                    raw_new_conf = (0.9 * current_conf) + (0.1 * instant_score)
                    change = raw_new_conf - current_conf
                    
                    if change > 0:
                        change = min(change, 0.05)
                    elif change < 0:
                        change = max(change, -0.03)
                        
                    final_conf = current_conf + change
                    
                    update_query = """
                        UPDATE trait 
                        SET confidence = %s, last_evidenced_at = NOW()
                        WHERE id = %s AND user_id = %s
                    """
                    cur.execute(update_query, (final_conf, existing_id, user_id))
                    print(f"Updated trait ID {existing_id}: Confidence shifted to {final_conf:.2f}")
                    
                else:
                    initial_conf = min(trait.confidence_suggestion, 0.5)
                    
                    insert_query = """
                        INSERT INTO trait (trait_text, trait_type, confidence, embedding, user_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cur.execute(insert_query, (
                        trait.trait_text, 
                        trait.trait_type, 
                        initial_conf, 
                        vector,
                        user_id
                    ))
                    print(f"Inserted new trait: '{trait.trait_text}'")