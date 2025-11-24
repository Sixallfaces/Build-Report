"""Pydantic models for request/response validation."""
from apps.models.work import WorkCreate, WorkUpdate, WorkResponse, WorkAddBalance
from apps.models.material import MaterialCreate, MaterialUpdate, MaterialResponse, MaterialAddQuantity
from apps.models.foreman import ForemanCreate, ForemanUpdate, ForemanResponse
from apps.models.report import ReportCreate, ReportUpdate, ReportResponse
from apps.models.category import CategoryCreate, CategoryUpdate, CategoryResponse
from apps.models.auth import LoginRequest, LoginResponse, UserResponse

__all__ = [
    'WorkCreate', 'WorkUpdate', 'WorkResponse', 'WorkAddBalance',
    'MaterialCreate', 'MaterialUpdate', 'MaterialResponse', 'MaterialAddQuantity',
    'ForemanCreate', 'ForemanUpdate', 'ForemanResponse',
    'ReportCreate', 'ReportUpdate', 'ReportResponse',
    'CategoryCreate', 'CategoryUpdate', 'CategoryResponse',
    'LoginRequest', 'LoginResponse', 'UserResponse',
]
