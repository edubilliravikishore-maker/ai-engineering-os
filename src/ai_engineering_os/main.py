"""FastAPI application entrypoint for AI Engineering OS."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from ai_engineering_os.config import get_settings
from ai_engineering_os.storage.database import (
    check_database_connection,
    close_database_connection,
)


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    app: str
    version: str
    environment: str
    database: str


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, Any]:
    """Manages application startup and graceful shutdown."""
    yield
    await close_database_connection()


app = FastAPI(
    title="AI Engineering OS",
    description="Deterministic Operating Layer for Multi-Agent Software Engineering",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Verifies application availability and PostgreSQL connectivity."""
    settings = get_settings()
    db_ok = await check_database_connection()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        app="ai-engineering-os",
        version="0.1.0",
        environment=settings.app_env,
        database="connected" if db_ok else "disconnected",
    )


@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """Root metadata endpoint."""
    return {
        "app": "AI Engineering OS",
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/health",
    }
