"""Semantic search over topics and ideas using embeddings."""

from __future__ import annotations

import os
from collections import defaultdict

from services.ideas_service import IdeaService
from utils.openAi import openai_client


def semantic_search_memories(query: str, user_id: str, n_topics: int = 5, k_ideas: int = 3):
    idea_service = IdeaService()
    query_embedding = openai_client.get_embeddings(query)[0].embedding
    topic_similarity_threshold = float(os.getenv("TOPIC_SIMILARITY_THRESHOLD", 0.7))
    idea_similarity_threshold = float(os.getenv("IDEA_SIMILARITY_THRESHOLD", 0.8))
    rows = idea_service.search_topics_and_ideas(
        query_embedding,
        user_id,
        n_topics,
        k_ideas,
        topic_similarity_threshold,
        idea_similarity_threshold,
    )
    topics = defaultdict(lambda: {"title": "", "summary": "", "ideas": []})

    for row in rows:
        topic_id = row["topic_id"]

        topics[topic_id]["title"] = row["title"]
        topics[topic_id]["summary"] = row["summary"]
        topics[topic_id]["similarity"] = row["topic_similarity"]
        topics[topic_id]["ideas"].append({
            "id": row["idea_id"],
            "content": row["idea_content"],
            "similarity": row["idea_similarity"],
        })

    return [{"topic_id": tid, **data} for tid, data in topics.items()]
