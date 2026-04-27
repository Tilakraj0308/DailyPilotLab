"""Trait extraction LLM call and full refresh pipeline."""

from __future__ import annotations

import json
import logging
import os

import yaml

from models.traits import TraitExtractionResponse
from services.topics_service import TopicsService
from services.trait_service import TraitsService
from utils.openAi import openai_client

logger = logging.getLogger(__name__)


def extract_traits(payload_for_llm: str) -> TraitExtractionResponse:
    """
    Calls the LLM with the trait-extraction prompt and returns structured TraitCandidate objects.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(root, "config", "prompts", "trait-extraction.yaml")
    with open(prompt_path, "r") as f:
        template = yaml.safe_load(f)

    system_prompt = template["system_prompt"]
    user_prompt = template["user_prompt_template"].format(payload_for_llm=payload_for_llm)

    completion = openai_client.get_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format=TraitExtractionResponse,
    )
    return completion


def update_traits(user_id: str):
    """
    Full pipeline to refresh user traits from high-signal topics and recent ideas.
    """
    topics_service = TopicsService()
    traits_service = TraitsService(openai_client=openai_client.client)

    recency_threshold = os.getenv("RECENCY_THRESHOLD", 5)
    dominance_threshold = os.getenv("DOMINANCE_THRESHOLD", 15)
    recent_ideas_per_topic = os.getenv("RECENT_IDEAS_PER_TOPIC", 3)

    high_signal_topics = topics_service.get_high_signal_topics(
        user_id=user_id,
        recency_threshold=recency_threshold,
        dominance_threshold=dominance_threshold,
    )

    if not high_signal_topics:
        return {
            "status": 200,
            "message": "No high-signal topics found; traits not updated.",
            "traits_processed": 0,
        }

    topic_payloads = []
    for topic in high_signal_topics:
        recent_ideas = topics_service.get_recent_ideas_for_topic(
            topic_id=topic["id"],
            user_id=user_id,
            limit=recent_ideas_per_topic,
        )
        topic_payloads.append({
            "topic_title": topic["title"],
            "topic_summary": topic["summary"],
            "memory_snippets": [idea["content"] for idea in recent_ideas],
        })

    payload_for_llm = json.dumps(topic_payloads, indent=2)
    logger.debug("traits payload_for_llm length=%s", len(payload_for_llm))

    extraction_response = extract_traits(payload_for_llm)
    traits_service.process_and_upsert_traits(extraction_response.traits, user_id)

    return {
        "status": 200,
        "message": "Traits updated successfully.",
        "traits_processed": len(extraction_response.traits),
    }
