"""Pydantic models for Categories."""
from pydantic import BaseModel, Field
from typing import Optional


class CategoryBase(BaseModel):
    """Base model for Category."""
    name: str = Field(..., min_length=1, max_length=255, description="Category name")


class CategoryCreate(CategoryBase):
    """Model for creating a new category."""
    pass


class CategoryUpdate(BaseModel):
    """Model for updating an existing category."""
    name: str = Field(..., min_length=1, max_length=255, description="New category name")


class CategoryResponse(CategoryBase):
    """Response model for Category."""
    id: int = Field(..., description="Category ID")
    created_date: Optional[str] = Field(None, description="Creation date")

    class Config:
        from_attributes = True
