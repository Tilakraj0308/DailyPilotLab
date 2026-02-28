from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Union

from pydantic import BaseModel, Field, ConfigDict

class TopicCreateInput(BaseModel):
    title: str = Field(description="Topic title")
    summary: str = Field(description="Topic summary")
    idea_ids: Optional[List[int]] = Field(default=[], description="List of idea IDs")
    # activity_7d: int = Field(default=0, description="7-day activity count")
    # activity_30d: int = Field(default=0, description="30-day activity count")
    # lifetime_size: int = Field(default=0, description="Total lifetime size")
    # is_archived: bool = Field(default=False, description="Archive status")
    # recency_strength: float = Field(default=0.0, description="Recency strength score")
    # dominance: float = Field(default=0.0, description="Dominance score")


class TopicUpdateInput(BaseModel):
    id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    # activity_7d: Optional[int] = None
    # activity_30d: Optional[int] = None
    # lifetime_size: Optional[int] = None
    # last_activity_at: Optional[time] = None
    # is_archived: Optional[bool] = None
    # recency_strength: Optional[float] = None
    # dominance: Optional[float] = None
    idea_ids: Optional[List[int]] = Field(default=[], description="List of idea IDs")


# class TopicDeleteInput(BaseModel):
#     id: int


# class TopicOut(BaseModel):
#     id: int
#     created_at: datetime
#     updated_at: Optional[datetime] = None
#     title: str
#     summary: str
#     summary_embedding: Optional[Union[List[float], str]] = None
#     activity_7d: int
#     activity_30d: int
#     lifetime_size: int
#     last_activity_at: Optional[time] = None
#     is_archived: bool
#     recency_strength: float
#     dominance: float
#     model_config = ConfigDict(from_attributes=True)
