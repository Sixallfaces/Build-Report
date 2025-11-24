"""Pydantic models for Materials."""
from pydantic import BaseModel, Field
from typing import Optional


class MaterialBase(BaseModel):
    """Base model for Material."""
    name: str = Field(..., min_length=1, max_length=255, description="Material name")
    category: str = Field(..., min_length=1, max_length=255, description="Category/section")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement")
    quantity: float = Field(default=0, ge=0, description="Quantity in stock")
    is_active: bool = Field(default=True, description="Is material active")
    unit_cost_without_vat: float = Field(default=0, ge=0, description="Unit cost without VAT")
    total_cost_without_vat: float = Field(default=0, ge=0, description="Total cost without VAT")


class MaterialCreate(MaterialBase):
    """Model for creating a new material."""
    pass


class MaterialUpdate(BaseModel):
    """Model for updating an existing material."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=255)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)
    quantity: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    unit_cost_without_vat: Optional[float] = Field(None, ge=0)
    total_cost_without_vat: Optional[float] = Field(None, ge=0)


class MaterialAddQuantity(BaseModel):
    """Model for adding quantity to material stock."""
    amount: float = Field(..., description="Amount to add to stock")
    performed_by: Optional[str] = Field(None, description="Who performed the action")
    description: Optional[str] = Field(None, description="Description of the change")


class MaterialPricingUpdate(BaseModel):
    """Model for updating material pricing."""
    unit_cost_without_vat: float = Field(..., ge=0, description="Unit cost without VAT")


class MaterialResponse(MaterialBase):
    """Response model for Material."""
    id: int = Field(..., description="Material ID")
    created_at: Optional[str] = Field(None, description="Creation date")

    # Calculated fields with VAT
    unit_cost_with_vat: Optional[float] = Field(None, description="Unit cost with VAT")
    total_cost_with_vat: Optional[float] = Field(None, description="Total cost with VAT")

    class Config:
        from_attributes = True


class MaterialHistoryEntry(BaseModel):
    """Model for material history entry."""
    id: int
    material_id: int
    material_name: Optional[str] = None
    material_unit: Optional[str] = None
    change_type: str
    change_amount: float
    resulting_quantity: Optional[float] = None
    performed_by: Optional[str] = None
    description: Optional[str] = None
    created_at: str
