"""Pydantic models for Works."""
from pydantic import BaseModel, Field
from typing import Optional


class WorkBase(BaseModel):
    """Base model for Work."""
    name: str = Field(..., min_length=1, max_length=255, description="Work name")
    category: str = Field(..., min_length=1, max_length=255, description="Category/section")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement")
    balance: float = Field(default=0, ge=0, description="Available balance")
    project_total: float = Field(default=0, ge=0, description="Project total quantity")
    is_active: bool = Field(default=True, description="Is work active")
    unit_cost_without_vat: float = Field(default=0, ge=0, description="Unit cost without VAT")
    total_cost_without_vat: float = Field(default=0, ge=0, description="Total cost without VAT")


class WorkCreate(WorkBase):
    """Model for creating a new work."""
    pass


class WorkUpdate(BaseModel):
    """Model for updating an existing work."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=255)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    balance: Optional[float] = Field(None, ge=0)
    project_total: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    unit_cost_without_vat: Optional[float] = Field(None, ge=0)
    total_cost_without_vat: Optional[float] = Field(None, ge=0)


class WorkAddBalance(BaseModel):
    """Model for adding balance to a work."""
    amount: float = Field(..., description="Amount to add to balance")


class WorkResponse(WorkBase):
    """Response model for Work."""
    id: int = Field(..., description="Work ID")

    # Calculated fields with VAT
    unit_cost_with_vat: Optional[float] = Field(None, description="Unit cost with VAT")
    total_cost_with_vat: Optional[float] = Field(None, description="Total cost with VAT")

    class Config:
        from_attributes = True


class WorkMaterialLink(BaseModel):
    """Model for linking work with material."""
    material_id: int = Field(..., description="Material ID")
    quantity_per_unit: float = Field(..., ge=0, description="Material quantity per work unit")


class WorkMaterialsUpdate(BaseModel):
    """Model for updating work materials."""
    materials: list[WorkMaterialLink] = Field(default=[], description="List of materials for the work")
