"""LLM topic organization and assign-unassigned-ideas flow."""

from __future__ import annotations

import json
import os
from typing import Any

import yaml

from models.output_schemas import TopicsList
from models.topics import TopicCreateInput, TopicUpdateInput
from services.ideas_service import IdeaService
from utils.openAi import openai_client
from utils.topic_manager import get_all_topics, update_topics, create_topics


def organize_ideas_into_topics(ideas: Any, existing_topics: Any) -> TopicsList:
    """
    Organizes ideas into topics using LLM.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    prompt_path = os.path.join(root, "config", "prompts", "topic_organization.yaml")
    with open(prompt_path, "r") as f:
        template = yaml.safe_load(f)

    ideas_data = []
    for idea in ideas:
        ideas_data.append({
            "id": idea["id"],
            "content": idea["content"],
        })

    existing_topics_data = []
    for topic in existing_topics:
        existing_topics_data.append({
            "id": topic["id"],
            "title": topic["title"],
            "summary": topic["summary"],
        })

    system_prompt = template["system_prompt"]

    user_prompt = template["user_prompt_template"].format(
        existing_topics=json.dumps(existing_topics_data, indent=2),
        ideas=json.dumps(ideas_data, indent=2),
    )

    completion = openai_client.get_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format=TopicsList,
    )
    return completion


def assign_idea_to_topic(user_id: str):
    """Assign unassigned ideas to existing topics using a threshold and create a new topic if needed."""
    threshold = float(os.getenv("TOPIC_ASSIGNMENT_THRESHOLD_SIMILARITY", 0.9))
    threshold = 1 - threshold
    idea_service = IdeaService()
    idea_service.assign_idea_to_topic(threshold, user_id)
    unassigned_ideas = idea_service.get_unassigned_ideas(user_id)
    existing_topics = get_all_topics(user_id)
    if len(unassigned_ideas) == 0:
        return {"status": 200, "message": "Assigned ideas successfully"}
    ideas = organize_ideas_into_topics(unassigned_ideas, existing_topics)
    new_topics, existing_topic_updates = [], []
    for topic in ideas.topics:
        if topic.is_new:
            new_topics.append(
                TopicCreateInput.model_validate(topic.model_dump(exclude={"is_new", "id"}))
            )
        else:
            existing_topic_updates.append(
                TopicUpdateInput.model_validate(topic.model_dump(exclude={"is_new"}))
            )
    if len(existing_topic_updates) > 0:
        update_topics(existing_topic_updates, user_id, append_idea_ids=True)
    if len(new_topics) > 0:
        create_topics(new_topics, user_id)
    return {"status": 200, "message": "Assigned ideas successfully"}
