"""Pydantic models for Foremen."""
from pydantic import BaseModel, Field
from typing import Optional, List


class ForemanBase(BaseModel):
    """Base model for Foreman."""
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    position: str = Field(..., min_length=2, max_length=100, description="Position/role")
    username: Optional[str] = Field(None, max_length=100, description="Telegram username")
    is_active: bool = Field(default=True, description="Is foreman active")


class ForemanCreate(ForemanBase):
    """Model for creating a new foreman."""
    pass


class ForemanUpdate(BaseModel):
    """Model for updating an existing foreman."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    position: Optional[str] = Field(None, min_length=2, max_length=100)
    username: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class ForemanResponse(ForemanBase):
    """Response model for Foreman."""
    id: int = Field(..., description="Foreman ID (Telegram user ID)")
    registration_date: Optional[str] = Field(None, description="Registration date")
    # For backward compatibility
    first_name: Optional[str] = Field(None, description="First name (alias for full_name)")
    last_name: Optional[str] = Field(None, description="Last name (alias for position)")

    class Config:
        from_attributes = True


class ForemanSectionUpdate(BaseModel):
    """Model for updating foreman sections."""
    category_ids: List[int] = Field(default=[], description="List of category IDs")


class ForemanSectionResponse(BaseModel):
    """Response model for foreman sections."""
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
