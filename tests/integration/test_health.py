"""Integration tests for FastAPI health and root endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    """Verifies that the /health endpoint responds with valid status payload."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "ai-engineering-os"
    assert data["version"] == "0.1.0"
    assert "status" in data
    assert "environment" in data
    assert "database" in data


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient) -> None:
    """Verifies that the root / endpoint responds with metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "AI Engineering OS"
    assert data["version"] == "0.1.0"
    assert data["docs_url"] == "/docs"
