"""LLM refinement of raw ideas."""

from __future__ import annotations

import json
import os

import yaml

from models.output_schemas import RefinedIdeaList
from utils.openAi import openai_client


def refine_raw_ideas(raw_ideas: list[str]):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(root, "config", "prompts", "idea_refiner.yaml")
    with open(prompt_path, "r") as f:
        template = yaml.safe_load(f)

    system_prompt = template["system"]

    user_prompt = template["user"].format(
        raw_ideas=json.dumps(raw_ideas, indent=2),
    )

    completion = openai_client.get_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_format=RefinedIdeaList,
    )
    return completion
