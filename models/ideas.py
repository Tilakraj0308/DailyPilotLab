# app/models/idea.py

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Union

from pydantic import BaseModel, Field, ConfigDict


# Ideas related models

class IdeaCreateInput(BaseModel):
    content: str = Field(default="", description="Idea content/text")
    topic_id: Optional[int] = Field(default=None, description="Topic reference (if used)")
    cluster_id: Optional[int] = Field(default=None, description="Cluster id from clustering pipeline")


class IdeaUpdateInput(BaseModel):
    id: int
    content: Optional[str] = None
    topic_id: Optional[int] = None
    cluster_id: Optional[int] = None


class IdeaDeleteInput(BaseModel):
    id: int


class IdeaOut(BaseModel):
    id: int
    created_at: datetime
    content: str = ""
    embeddings: Optional[Union[List[float], str]] = None
    topic_id: Optional[int] = None
    cluster_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# Topics related models

class TopicCreateInput(BaseModel):
    title: str = Field(description="Topic title")
    summary: str = Field(description="Topic summary")
    activity_7d: int = Field(default=0, description="7-day activity count")
    activity_30d: int = Field(default=0, description="30-day activity count")
    lifetime_size: int = Field(default=0, description="Total lifetime size")
    is_archived: bool = Field(default=False, description="Archive status")
    recency_strength: float = Field(default=0.0, description="Recency strength score")
    dominance: float = Field(default=0.0, description="Dominance score")


class TopicUpdateInput(BaseModel):
    id: int
    title: Optional[str] = None
    summary: Optional[str] = None
    activity_7d: Optional[int] = None
    activity_30d: Optional[int] = None
    lifetime_size: Optional[int] = None
    last_activity_at: Optional[time] = None
    is_archived: Optional[bool] = None
    recency_strength: Optional[float] = None
    dominance: Optional[float] = None


class TopicDeleteInput(BaseModel):
    id: int


class TopicOut(BaseModel):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    title: str
    summary: str
    summary_embedding: Optional[Union[List[float], str]] = None
    activity_7d: int
    activity_30d: int
    lifetime_size: int
    last_activity_at: Optional[time] = None
    is_archived: bool
    recency_strength: float
    dominance: float
    model_config = ConfigDict(from_attributes=True)
