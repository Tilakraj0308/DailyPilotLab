from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

class ClassificationResult(BaseModel):
    category: Literal["idea", "personal_information", "secrets", "gibberish"]
    confidence: float = Field(description="A score between 0 and 1")


class PersonalInfoItem(BaseModel):
    key: str = Field(
        description="The name of the personal information type (e.g., 'occupation', 'birth_city', 'favorite_color'). Use snake_case if possible."
    )
    value: str = Field(
        description="The actual value associated with the key (e.g., 'Software Engineer', 'Paris', 'Blue')."
    )

class PersonalState(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    personal_info: List[PersonalInfoItem] = Field(
        description="A collection of extracted personal details."
    )

class Topic(BaseModel):
    """Represents a single topic with its metadata and assigned idea IDs."""
    model_config = ConfigDict(extra='forbid')
    title: str = Field(
        description="Clear, descriptive title for the topic (e.g., 'Linguistic Paradoxes and Language Play', 'The Psychology of Pretending')."
    )
    summary: str = Field(
        description="Concise explanation of the theme connecting the ideas in this topic."
    )
    idea_ids: List[int] = Field(
        description="List of idea IDs assigned to this topic. An idea can be assigned to multiple topics if it genuinely fits multiple themes."
    )
    is_new: bool = Field(
        description="Whether this is a newly created topic (true) or an existing topic with new assignments (false)."
    )

class TopicsList(BaseModel):
    """A list of topics."""
    topics: List[Topic]
    
# class TopicOrganization(BaseModel):
#     """Complete organization of ideas into topics."""    
#     model_config = ConfigDict(extra='forbid')
#     topics: List[Topic] = Field(
#         description="A collection of all topics (both existing topics with new idea assignments and newly created topics)."
#     )    
#     unassigned_idea_ids: List[int] = Field(
#         default_factory=list,
#         description="List of idea IDs that couldn't be confidently assigned to any topic. Should be empty or minimal in most cases."
#     )
#     reasoning: str = Field(
#         default="",
#         description="Brief explanation of the organization strategy and any notable decisions made during topic assignment."
#     )