# app/models/idea.py

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Union

from pydantic import BaseModel, Field


class IdeaCreate(BaseModel):
    content: str = Field(default="", description="Idea content/text")
    embeddings: Optional[Union[List[float], str]] = Field(
        default=None,
        description="Vector embedding. Can be list[float] or a pgvector string representation.",
    )
    topic_id: Optional[int] = Field(default=None, description="Topic reference (if used)")
    cluster_id: Optional[int] = Field(default=None, description="Cluster id from clustering pipeline")


class IdeaUpdate(BaseModel):
    content: Optional[str] = None
    embeddings: Optional[Union[List[float], str]] = None
    topic_id: Optional[int] = None
    cluster_id: Optional[int] = None


class IdeaOut(BaseModel):
    id: int
    created_at: datetime
    content: str = ""
    embeddings: Optional[Union[List[float], str]] = None
    topic_id: Optional[int] = None
    cluster_id: Optional[int] = None
