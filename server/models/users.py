from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict


class GoogleAuthRequest(BaseModel):
    """Payload sent by the React Native client after Google Sign-In."""
    id_token: str


class UserOut(BaseModel):
    """Public user representation returned in API responses."""
    id: int
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    """Response returned after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    user: UserOut
