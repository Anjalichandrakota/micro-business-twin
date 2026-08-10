"""
Pydantic schemas for authentication requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Requests ---

class RegisterRequest(BaseModel):
    """Body for POST /api/auth/register."""
    name: str = Field(..., min_length=1, max_length=150, examples=["Ravi Kumar"])
    email: EmailStr = Field(..., examples=["ravi@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["securepassword"])


class LoginRequest(BaseModel):
    """Body for POST /api/auth/login."""
    email: EmailStr = Field(..., examples=["ravi@example.com"])
    password: str = Field(..., examples=["securepassword"])


# --- Responses ---

class TokenResponse(BaseModel):
    """Returned after successful login."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user information returned by GET /api/auth/me."""
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
