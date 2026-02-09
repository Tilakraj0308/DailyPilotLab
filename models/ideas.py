# app/models/idea.py

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Union

from pydantic import BaseModel, Field, ConfigDict


# Ideas related models

class IdeaCreateInput(BaseModel):
    content: str = Field(default="", description="Idea content/text")
    # topic_ids: Optional[List[int]] = Field(default=None, description="Topic references (if used)")
    # cluster_id: Optional[int] = Field(default=None, description="Cluster id from clustering pipeline")


class IdeaUpdateInput(BaseModel):
    id: int
    content: Optional[str] = None
    topic_ids: Optional[List[int]] = None
    cluster_id: Optional[int] = None


class IdeaDeleteInput(BaseModel):
    id: int


class IdeaOut(BaseModel):
    id: int
    created_at: datetime
    content: str = ""
    embeddings: Optional[Union[List[float], str]] = None
    topic_ids: Optional[List[int]] = None
    cluster_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

