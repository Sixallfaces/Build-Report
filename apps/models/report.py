"""Pydantic models for Work Reports."""
from pydantic import BaseModel, Field
from typing import Optional, List


class ReportBase(BaseModel):
    """Base model for Work Report."""
    foreman_id: int = Field(..., description="Foreman ID")
    work_id: int = Field(..., description="Work ID")
    quantity: float = Field(..., gt=0, description="Quantity of work done")
    photo_report_url: Optional[str] = Field(None, description="Photo report URL")


class ReportCreate(ReportBase):
    """Model for creating a new work report."""
    pass


class ReportUpdate(BaseModel):
    """Model for updating an existing work report."""
    quantity: Optional[float] = Field(None, gt=0)
    photo_report_url: Optional[str] = None
    is_verified: Optional[bool] = None


class ReportVerify(BaseModel):
    """Model for verifying a report."""
    is_verified: bool = Field(..., description="Verification status")


class ReportResponse(ReportBase):
    """Response model for Work Report."""
    id: int = Field(..., description="Report ID")
    report_date: str = Field(..., description="Report date (YYYY-MM-DD)")
    report_time: str = Field(..., description="Report time (HH:MM:SS)")
    is_verified: bool = Field(default=False, description="Is report verified")

    # Joined fields
    work_name: Optional[str] = Field(None, description="Work name")
    work_category: Optional[str] = Field(None, description="Work category")
    work_unit: Optional[str] = Field(None, description="Work unit")
    foreman_name: Optional[str] = Field(None, description="Foreman name")
    foreman_position: Optional[str] = Field(None, description="Foreman position")

    class Config:
        from_attributes = True


class DailyReportSummary(BaseModel):
    """Summary of reports for a specific date."""
    foreman: str
    position: Optional[str] = None
    works: List[dict]


class AccumulativeStatementEntry(BaseModel):
    """Entry in the accumulative statement."""
    category: str = Field(..., alias="Раздел")
    work_name: str = Field(..., alias="Работа")
    unit: str = Field(..., alias="Единица измерения")
    unit_cost: float = Field(default=0, alias="Стоимость за единицу")
    quantity: float = Field(..., alias="Количество")
    project_total: float = Field(..., alias="Проект")
    completion_percentage: float = Field(..., alias="%Выполнения")
    total_cost: float = Field(default=0, alias="Сумма")

    class Config:
        populate_by_name = True
