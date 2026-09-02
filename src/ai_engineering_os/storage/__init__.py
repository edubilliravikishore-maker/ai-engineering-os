"""Relational persistence for AI Engineering OS (ADR-005).

PostgreSQL is the durable source of truth; domain objects are the behavioural
representation loaded from that state (ADR-005 5.3).

This layer owns SQLAlchemy models, domain <-> row mappers, repositories, the Unit
of Work session mechanism, persistence exceptions, and Alembic migrations. It
owns **no** domain logic, **no** business transaction boundary, and **no**
dependency on ``rules``.

Two boundaries are structural rather than conventional, and both are pinned by
test:

* **``storage`` never imports ``rules``**, and ``rules`` never imports
  ``storage`` (Blueprint 3, ADR-004 4.4). There is deliberately no context
  loader here: that component belongs to the Checkpoint 6 Kernel.
* **A SQLAlchemy model never leaves this package** (ADR-005 5.11). Repositories
  return frozen domain objects, so nothing upstream holds a live database row.
"""

from ai_engineering_os.storage.database import (
    Base,
    check_database_connection,
    close_database_connection,
    get_db_session,
    get_engine,
    get_session_factory,
)
from ai_engineering_os.storage.errors import (
    AppendOnlyViolationError,
    ConcurrencyConflictError,
    DomainReconstructionError,
    IntegrityConstraintError,
    NotFoundError,
    PersistenceError,
)
from ai_engineering_os.storage.unit_of_work import UnitOfWork, unit_of_work

__all__ = [
    "AppendOnlyViolationError",
    "Base",
    "ConcurrencyConflictError",
    "DomainReconstructionError",
    "IntegrityConstraintError",
    "NotFoundError",
    "PersistenceError",
    "UnitOfWork",
    "check_database_connection",
    "close_database_connection",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "unit_of_work",
]
