"""Personal memory file + LLM classification for ideas vs personal info."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Tuple

import yaml

from models.output_schemas import ClassificationResultList, PersonalState
from utils.openAi import openai_client


def _server_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def classify_ideas(user_input_text: list[Tuple[str, str]]):
    root = _server_root()
    personal_state_path = os.path.join(root, "config", "memory", "personal_state.json")

    if os.path.exists(personal_state_path):
        with open(personal_state_path, "r") as f:
            personal_state_data = f.read().strip()

        if not personal_state_data:
            personal_state_data = "{}"
    else:
        personal_state_data = "{}"

    idea_filter_prompt_path = os.path.join(root, "config", "prompts", "ideaFiltering.yaml")
    with open(idea_filter_prompt_path, "r") as f:
        template = yaml.safe_load(f)

    system_msg = template["system"].format(personal_state=personal_state_data)
    user_msg = template["user"].format(user_input=json.dumps(user_input_text))

    completion = openai_client.get_chat_completion(
        system_prompt=system_msg,
        user_prompt=user_msg,
        response_format=ClassificationResultList,
    )

    return completion


def update_personal_state(user_input_text: list[str], user_id: str | None = None) -> None:
    """
    Merge classified personal snippets into config/memory/personal_state.json.

    Args:
        user_input_text: Text snippets classified as personal_information.
        user_id: Reserved for future per-user memory files; ignored today.
    """
    _ = user_id
    root = _server_root()
    personal_state_path = os.path.join(root, "config", "memory", "personal_state.json")

    if os.path.exists(personal_state_path):
        with open(personal_state_path, "r") as f:
            personal_state_data = f.read().strip()

        if not personal_state_data:
            personal_state_data = "{}"
    else:
        personal_state_data = "{}"

    personal_info_updater_prompt_path = os.path.join(
        root, "config", "prompts", "personal_info_updater.yaml"
    )
    with open(personal_info_updater_prompt_path, "r") as f:
        template = yaml.safe_load(f)

    system_msg = template["system"].format(personal_state=personal_state_data)
    user_msg = template["user"].format(user_input=json.dumps(user_input_text))

    completion = openai_client.get_chat_completion(
        system_prompt=system_msg,
        user_prompt=user_msg,
        response_format=PersonalState,
    )

    data_store: defaultdict[str, list] = defaultdict(list)
    for item in completion.personal_info:
        data_store[item.key].append(item.value)

    final_dict = {k: (v[0] if len(v) == 1 else v) for k, v in data_store.items()}

    with open(personal_state_path, "w") as f:
        json.dump(final_dict, f, indent=2)
