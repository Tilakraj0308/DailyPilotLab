"""
Onboarding service — loads question config and processes answers.
"""

import json
import os
from services.user_service import mark_onboarding_complete

QUESTIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "onboarding_questions.json")


def get_questions() -> list:
    """Return the onboarding question set from config."""
    with open(QUESTIONS_PATH, "r") as f:
        return json.load(f)


def submit_answers(user_id: str, answers: dict) -> dict:
    """
    Process submitted onboarding answers into personal_state and mark complete.
    
    `answers` is a flat dict like:
    {
        "nickname": "Alex",
        "date_of_birth": "1998-03-15",
        "occupation": "Student",
        "study_topic": "Machine Learning",
        "additional_info": "I love hiking"
    }
    """
    # Build personal_state from answers using the question config's state_key mapping
    questions = get_questions()
    valid_keys = {q["state_key"] for q in questions}

    personal_state = {}
    for key, value in answers.items():
        if key in valid_keys and value:
            personal_state[key] = value

    mark_onboarding_complete(user_id, personal_state)

    return {"status": "success", "personal_state": personal_state}
