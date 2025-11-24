"""Pydantic models for Authentication."""
from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """Model for login request."""
    username: str = Field(..., min_length=1, max_length=100, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class LoginResponse(BaseModel):
    """Model for login response."""
    success: bool = Field(..., description="Login success status")
    message: str = Field(..., description="Response message")
    user: Optional["UserResponse"] = Field(None, description="User data if login successful")


class UserResponse(BaseModel):
    """Response model for User."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Is user active")
    created_date: Optional[str] = Field(None, description="Creation date")
    last_login: Optional[str] = Field(None, description="Last login date")

    class Config:
        from_attributes = True


# Update forward reference
LoginResponse.model_rebuild()
