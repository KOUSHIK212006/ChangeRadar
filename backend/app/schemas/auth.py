"""Pydantic schemas for authentication and user identity."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 characters)")
    full_name: Optional[str] = Field(None, max_length=255, description="User full display name")


class UserLoginRequest(BaseModel):
    """Payload for user authentication."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Public user identity representation."""

    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Signed JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifespan in seconds")


class AuthResponse(BaseModel):
    """Combined authentication response containing user profile and bearer token."""

    user: UserResponse
    token: TokenResponse
