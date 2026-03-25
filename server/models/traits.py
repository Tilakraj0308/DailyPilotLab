# models/traits.py
from pydantic import BaseModel, Field
from typing import List

# 1. The structured output we will demand from the LLM
class TraitCandidate(BaseModel):
    trait_text: str = Field(description="A concise statement of the user's trait")
    trait_type: str = Field(description="Must be exactly one of: interest, goal, skill, routine, workstyle, preference, avoidance, value, constraint")
    confidence_suggestion: float = Field(description="Estimated confidence from 0.0 to 1.0 based on the evidence provided", ge=0.0, le=1.0)
    evidence_bullet: str = Field(description="A single sentence quoting the raw ideas that prove this trait")

# 2. A wrapper for OpenAI's structured output
class TraitExtractionResponse(BaseModel):
    traits: List[TraitCandidate]