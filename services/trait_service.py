# services/traits_service.py
from database.connection import get_dict_cursor # Adjust import based on your actual db connection file
from models.traits import TraitCandidate
from typing import List

class TraitsService:
    def __init__(self, openai_client):
        # Pass your existing OpenAI client wrapper so we can generate embeddings
        self.openai_client = openai_client

    def process_and_upsert_traits(self, new_traits: List[TraitCandidate]):
        """
        Embeds new traits, checks for semantic duplicates, and applies EMA smoothing.
        """
        for trait in new_traits:
            # 1. Get the embedding for the semantic search
            # (Adjust this method call based on how your openai_client is structured)
            embedding_response = self.openai_client.embeddings.create(
                input=trait.trait_text, 
                model="text-embedding-3-small" 
            )
            vector = embedding_response.data[0].embedding
            
            # 2. Search for existing traits that are highly similar (cosine distance <= 0.12)
            search_query = """
                SELECT id, confidence 
                FROM trait
                WHERE (embedding <=> %s::vector) <= 0.12
                ORDER BY embedding <=> %s::vector
                LIMIT 1
            """
            
            with get_dict_cursor() as cur:
                cur.execute(search_query, (vector, vector))
                match = cur.fetchone()
                
                if match:
                    # --- UPDATE EXISTING TRAIT (Apply EMA) ---
                    existing_id = match['id']
                    current_conf = float(match['confidence'])
                    instant_score = trait.confidence_suggestion
                    
                    # Calculate new raw confidence: 90% history, 10% new evidence
                    raw_new_conf = (0.9 * current_conf) + (0.1 * instant_score)
                    change = raw_new_conf - current_conf
                    
                    # Cap the drift (+0.05 max increase, -0.03 max decrease per run)
                    if change > 0:
                        change = min(change, 0.05)
                    elif change < 0:
                        change = max(change, -0.03)
                        
                    final_conf = current_conf + change
                    
                    update_query = """
                        UPDATE trait 
                        SET confidence = %s, last_evidenced_at = NOW()
                        WHERE id = %s
                    """
                    cur.execute(update_query, (final_conf, existing_id))
                    print(f"Updated trait ID {existing_id}: Confidence shifted to {final_conf:.2f}")
                    
                else:
                    # --- INSERT BRAND NEW TRAIT ---
                    # Start conservative: cap initial confidence at 0.5
                    initial_conf = min(trait.confidence_suggestion, 0.5)
                    
                    insert_query = """
                        INSERT INTO trait (trait_text, trait_type, confidence, embedding)
                        VALUES (%s, %s, %s, %s)
                    """
                    cur.execute(insert_query, (
                        trait.trait_text, 
                        trait.trait_type, 
                        initial_conf, 
                        vector
                    ))
                    print(f"Inserted new trait: '{trait.trait_text}'")