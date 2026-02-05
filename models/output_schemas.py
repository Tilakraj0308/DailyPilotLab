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