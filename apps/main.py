"""
Main FastAPI application entry point.
Build-Report API Server - Modular Architecture
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.config import settings
from apps.database import init_database, upgrade_database
from apps.routers import (
    works_router,
    materials_router,
    foremen_router,
    reports_router,
    categories_router,
    auth_router,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('main')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("Starting Build-Report API Server...")
    await init_database()
    await upgrade_database()
    logger.info("Database initialized and upgraded")
    yield
    # Shutdown
    logger.info("Shutting down Build-Report API Server...")


# Create FastAPI application
app = FastAPI(
    title="Build-Report API",
    description="API для системы учета строительных работ",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(works_router)
app.include_router(materials_router)
app.include_router(foremen_router)
app.include_router(reports_router)
app.include_router(categories_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Build-Report API",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "apps.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
