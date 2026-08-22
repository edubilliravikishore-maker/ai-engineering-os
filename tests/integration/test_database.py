"""Integration tests for PostgreSQL database connectivity via SQLAlchemy."""

import pytest
from sqlalchemy import text

from ai_engineering_os.storage.database import (
    check_database_connection,
    get_session_factory,
)


@pytest.mark.asyncio
async def test_database_connectivity() -> None:
    """Verifies that the application connects to PostgreSQL successfully."""
    is_connected = await check_database_connection()
    assert is_connected is True, "Expected successful PostgreSQL database connection."


@pytest.mark.asyncio
async def test_direct_session_execution() -> None:
    """Verifies that queries can be executed over an async session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(text("SELECT 42 AS answer"))
        answer = result.scalar()
        assert answer == 42
