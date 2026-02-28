from typing import Literal, Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

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
    """Represents a single topic with its metadata and assigned idea IDs.

    Rules enforced at validation time:
    - is_new=False  → id and idea_ids are required; title and summary are optional.
    - is_new=True   → title, summary, and idea_ids are required; id must be omitted.
    """
    model_config = ConfigDict(extra='forbid')

    is_new: bool = Field(
        description="True if this is a newly created topic; false if it is an existing topic being updated."
    )
    id: Optional[int] = Field(
        default=None,
        description="Database ID of the topic. Required when is_new is false. Must be omitted when is_new is true."
    )
    title: Optional[str] = Field(
        default=None,
        description="Clear, descriptive title (e.g., 'Linguistic Paradoxes and Language Play'). Required when is_new is true."
    )
    summary: Optional[str] = Field(
        default=None,
        description="Concise explanation of the theme connecting the ideas. Required when is_new is true."
    )
    idea_ids: List[int] = Field(
        description="List of idea IDs assigned to this topic. An idea can belong to multiple topics."
    )

    @model_validator(mode="after")
    def check_conditional_fields(self) -> "Topic":
        if self.is_new:
            missing = [f for f in ("title", "summary") if not getattr(self, f)]
            if missing:
                raise ValueError(
                    f"Fields {missing} are required when is_new is True."
                )
        else:
            if self.id is None:
                raise ValueError("'id' is required when is_new is False.")
        return self

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