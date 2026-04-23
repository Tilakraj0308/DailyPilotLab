import os
import sys
import json
from datetime import datetime, timezone, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.dbConnection import get_dict_cursor
from utils.openAi import openai_client
from models.output_schemas import RefinedIdeaList
from services.ideas_service import IdeaService
from utils.topic_manager import get_all_topics
from utils.helpers import update_traits, assign_idea_to_topic

def get_all_users():
    with get_dict_cursor() as cur:
        cur.execute("SELECT auth_id FROM public.users")
        return [row["auth_id"] for row in cur.fetchall()]

def extract_ideas_from_recent_chats():
    print("[Memory Pipeline] Starting 4-Hour Extractor...")
    users = get_all_users()
    for user_id in users:
        with get_dict_cursor() as cur:
            cur.execute("""
                SELECT id, role, content, created_at 
                FROM public.chat_messages 
                WHERE user_id = %s AND processed_for_ideas = false
                ORDER BY created_at ASC
            """, (user_id,))
            unprocessed = cur.fetchall()

        if not unprocessed:
            continue

        # Group by 4 hour gap or older than 4 hours
        messages_to_process = []
        message_ids = []
        now = datetime.now(timezone.utc)
        
        last_time = None
        for msg in unprocessed:
            msg_time = msg["created_at"]
            if not msg_time.tzinfo:
                msg_time = msg_time.replace(tzinfo=timezone.utc)

            # Check if msg is older than 4 hours, or if gap > 4 hours
            if (now - msg_time) > timedelta(hours=4) or (last_time and (msg_time - last_time) > timedelta(hours=4)):
                messages_to_process.append(msg)
                message_ids.append(msg["id"])
            last_time = msg_time
            
        if not messages_to_process:
            continue

        print(f"[Memory Pipeline] Extracting ideas for user {user_id} ({len(messages_to_process)} messages)")
        
        # LLM prompt to extract atomic ideas
        chat_context = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages_to_process])
        
        system_prompt = "You are a context extractor. Extract discrete, standalone factual statements or preferences about the user from the provided chat logs. Format as concise singular atomic facts."
        user_prompt = f"Chat logs:\n{chat_context}"

        try:
            completion = openai_client.get_chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=RefinedIdeaList
            )
            
            atomic_ideas = completion.refined_ideas
            
            if atomic_ideas:
                texts_to_embed = [idea.refined_statement for idea in atomic_ideas]
                embeddings_data = openai_client.get_embeddings(texts_to_embed)
                
                final_ideas = []
                for idx, embedding_obj in enumerate(embeddings_data):
                    final_ideas.append({
                        'content': texts_to_embed[idx],
                        'embeddings': embedding_obj.embedding,
                        'raw': False,
                        'status': 'active'
                    })
                
                service = IdeaService()
                service.bulk_create_ideas(final_ideas, user_id)
                print(f"[Memory Pipeline] Saved {len(final_ideas)} new atomic ideas.")

            # Mark processed
            with get_dict_cursor() as cur:
                cur.execute(
                    "UPDATE public.chat_messages SET processed_for_ideas = true WHERE id = ANY(%s)",
                    (message_ids,)
                )
        except Exception as e:
            print(f"[Memory Pipeline] Error extracting ideas: {e}")


def consolidate_24h_ideas():
    print("[Memory Pipeline] Starting 24-Hour Consolidator...")
    users = get_all_users()
    for user_id in users:
        with get_dict_cursor() as cur:
            # Find active ideas older than 24h
            cur.execute("""
                SELECT id 
                FROM public.raw_idea 
                WHERE user_id = %s AND status = 'active' AND created_at < NOW() - INTERVAL '24 HOURS'
            """, (user_id,))
            ideas_to_consolidate = [r["id"] for r in cur.fetchall()]
        
        if not ideas_to_consolidate:
            continue

        print(f"[Memory Pipeline] Consolidating {len(ideas_to_consolidate)} ideas for user {user_id}")
        
        # Step 1: Assign to topics
        try:
            assign_res = assign_idea_to_topic(user_id)
            print(f"[Memory Pipeline] Assignment: {assign_res.get('message', 'done')}")
        except Exception as e:
            print(f"[Memory Pipeline] Error assigning topics: {e}")

        # Step 2: Update traits
        try:
            update_res = update_traits(user_id)
            print(f"[Memory Pipeline] Traits update: {update_res.get('message', 'done')}")
        except Exception as e:
            print(f"[Memory Pipeline] Error updating traits: {e}")

        # Step 3: Mark as processed_to_long_term
        try:
            with get_dict_cursor() as cur:
                cur.execute("""
                    UPDATE public.raw_idea 
                    SET status = 'processed_to_long_term' 
                    WHERE id = ANY(%s)
                """, (ideas_to_consolidate,))
            print(f"[Memory Pipeline] Marked {len(ideas_to_consolidate)} ideas as long-term memory.")
        except Exception as e:
            print(f"[Memory Pipeline] Error marking long-term: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--extract', action='store_true')
    parser.add_argument('--consolidate', action='store_true')
    parser.add_argument('--all', action='store_true')
    args = parser.parse_args()

    if args.extract or args.all:
        extract_ideas_from_recent_chats()
    if args.consolidate or args.all:
        consolidate_24h_ideas()
