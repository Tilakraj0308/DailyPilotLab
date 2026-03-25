from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    """Public user representation returned in API responses."""
    id: int
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
