"""Fixtures for persistence integration tests against real PostgreSQL.

The schema is built by **Alembic**, never by ``create_all``: the migrations are
the artefact under test, and building the schema any other way would let a
migration defect pass unnoticed.

Isolation between tests is by ``TRUNCATE`` rather than drop-and-recreate, so the
Alembic version state is never disturbed by a test that did not intend to change
it.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    new_id,
)
from ai_engineering_os.storage.database import Base, get_engine, get_session_factory
from ai_engineering_os.storage.unit_of_work import UnitOfWork

_TABLES = ", ".join(sorted(Base.metadata.tables))


def _upgrade_to_head() -> None:
    """Applies every migration. Runs in a worker thread: Alembic drives its own loop."""
    command.upgrade(Config("alembic.ini"), "head")


async def _schema_is_current() -> bool:
    """Returns whether every mapped table already exists."""
    engine = get_engine()
    async with engine.connect() as connection:
        present = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    return set(Base.metadata.tables).issubset(present)


@pytest.fixture
async def migrated_database() -> None:
    """Guarantees the Alembic-managed schema is present, then empties every table."""
    if not await _schema_is_current():
        await asyncio.to_thread(_upgrade_to_head)

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest.fixture
async def uow(migrated_database: None) -> AsyncGenerator[UnitOfWork]:
    """Provides a Unit of Work over a clean schema.

    The fixture stands in for the transaction owner, which is the Checkpoint 6
    Kernel and does not exist yet (ADR-005 5.5).
    """
    _ = migrated_database
    session_factory = get_session_factory()
    async with session_factory() as session:
        work = UnitOfWork(session)
        async with work:
            yield work


@pytest.fixture
def coordinator() -> Actor:
    """An active Coordinator who can own a Feature."""
    return Actor(
        id=new_id(ActorId), role=ActorRole.COORDINATOR, name="auth-coordinator", domain="auth"
    )


@pytest.fixture
def worker() -> Actor:
    """An active backend Worker."""
    return Actor(
        id=new_id(ActorId),
        role=ActorRole.WORKER,
        name="backend-worker-1",
        domain="auth",
        capabilities=frozenset({CapabilityType.BACKEND}),
    )


@pytest.fixture
def reviewer() -> Actor:
    """An active Reviewer."""
    return Actor(id=new_id(ActorId), role=ActorRole.REVIEWER, name="reviewer-1")
