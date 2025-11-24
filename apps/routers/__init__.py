"""API Routers for Build-Report application."""
from apps.routers.works import router as works_router
from apps.routers.materials import router as materials_router
from apps.routers.foremen import router as foremen_router
from apps.routers.reports import router as reports_router
from apps.routers.categories import router as categories_router
from apps.routers.auth import router as auth_router

__all__ = [
    'works_router',
    'materials_router',
    'foremen_router',
    'reports_router',
    'categories_router',
    'auth_router',
]
