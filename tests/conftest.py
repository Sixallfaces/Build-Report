"""Pytest configuration and fixtures."""
import asyncio
import os
import tempfile
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Set test environment before importing app
os.environ['DATABASE_PATH'] = ':memory:'
os.environ['CORS_ORIGINS'] = 'http://localhost'
os.environ['BOT_TOKEN'] = 'test_token'
os.environ['YANDEX_DISK_TOKEN'] = 'test_token'

from apps.main import app
from apps.database import init_database, get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db():
    """Initialize test database."""
    # Create a temp file for SQLite
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DATABASE_PATH'] = path

    # Import settings after setting env var
    from apps.config import settings
    settings.DATABASE_PATH = path

    await init_database()
    yield path

    # Cleanup
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest_asyncio.fixture
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_work_data():
    """Sample work data for tests."""
    return {
        "name": "Test Work",
        "category": "Test Category",
        "unit": "шт",
        "balance": 100.0,
        "project_total": 500.0,
        "is_active": True,
        "unit_cost_without_vat": 150.0,
        "total_cost_without_vat": 15000.0
    }


@pytest.fixture
def sample_material_data():
    """Sample material data for tests."""
    return {
        "name": "Test Material",
        "category": "Test Category",
        "unit": "кг",
        "quantity": 50.0,
        "is_active": True,
        "unit_cost_without_vat": 100.0,
        "total_cost_without_vat": 5000.0
    }


@pytest.fixture
def sample_category_data():
    """Sample category data for tests."""
    return {
        "name": "Test Category"
    }


@pytest.fixture
def sample_foreman_data():
    """Sample foreman data for tests."""
    return {
        "full_name": "Иван Иванов",
        "position": "Бригадир",
        "username": "ivan_ivanov",
        "is_active": True
    }
