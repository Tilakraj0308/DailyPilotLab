"""
Legacy import surface for LLM + domain helpers.

Implementation is split into focused modules; import from those in new code:
`memory_state`, `topic_assignment`, `semantic_search`, `idea_refinement`, `traits_pipeline`.
"""

from utils.idea_refinement import refine_raw_ideas
from utils.memory_state import classify_ideas, update_personal_state
from utils.semantic_search import semantic_search_memories
from utils.topic_assignment import assign_idea_to_topic, organize_ideas_into_topics
from utils.traits_pipeline import extract_traits, update_traits

__all__ = [
    "assign_idea_to_topic",
    "classify_ideas",
    "extract_traits",
    "organize_ideas_into_topics",
    "refine_raw_ideas",
    "semantic_search_memories",
    "update_personal_state",
    "update_traits",
]
