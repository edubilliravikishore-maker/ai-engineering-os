"""Pytest test configuration and fixtures for AI Engineering OS."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from ai_engineering_os.config import Settings, get_settings
from ai_engineering_os.main import app
from ai_engineering_os.storage.database import close_database_connection


@pytest.fixture
def test_settings() -> Settings:
    """Provides application settings for test runs."""
    return get_settings()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient]:
    """Provides an asynchronous HTTP test client for the FastAPI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
async def cleanup_database_pool() -> AsyncGenerator[None]:
    """Cleans up database connection pool after each test."""
    yield
    await close_database_connection()
