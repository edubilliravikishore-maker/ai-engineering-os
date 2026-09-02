"""Unit of Work — the session-scope mechanism (ADR-005 5.5, Blueprint 2.2).

Blueprint 2.2 places the Unit of Work inside ``storage``. This module provides
the mechanism; it does **not** decide where a business transaction begins or
ends. That authority belongs to the service/use-case layer, which is the
Checkpoint 6 OS Kernel and does not exist yet.

The division matters. ``storage`` supplies *one session per transaction* and the
repositories bound to it. The **caller** decides when to ``commit``. A repository
that committed on its own would let a partially applied transition reach durable
storage, and the Validation-First invariant of Blueprint 7.2 depends on exactly
one component owning that moment.

Exiting the context without an explicit ``commit`` **rolls back**. An unfinished
transaction is never treated as a successful one.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Self

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engineering_os.storage.database import get_session_factory
from ai_engineering_os.storage.errors import PersistenceError
from ai_engineering_os.storage.repositories.actor_repo import ActorRepository
from ai_engineering_os.storage.repositories.decision_repo import DecisionRepository
from ai_engineering_os.storage.repositories.evidence_repo import EvidenceRepository
from ai_engineering_os.storage.repositories.feature_repo import FeatureRepository
from ai_engineering_os.storage.repositories.plan_repo import FeaturePlanRepository
from ai_engineering_os.storage.repositories.qa_repo import QAReportRepository
from ai_engineering_os.storage.repositories.review_decision_repo import ReviewDecisionRepository
from ai_engineering_os.storage.repositories.task_repo import TaskRepository
from ai_engineering_os.storage.repositories.task_revision_repo import TaskRevisionRepository
from ai_engineering_os.storage.repositories.work_package_repo import WorkPackageRepository

__all__ = ["UnitOfWork", "unit_of_work"]


class UnitOfWork:
    """One session, the repositories bound to it, and explicit commit control."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._committed = False

        self.actors = ActorRepository(session)
        self.features = FeatureRepository(session)
        self.feature_plans = FeaturePlanRepository(session)
        self.tasks = TaskRepository(session)
        self.task_revisions = TaskRevisionRepository(session)
        self.work_packages = WorkPackageRepository(session)
        self.evidence = EvidenceRepository(session)
        self.qa_reports = QAReportRepository(session)
        self.review_decisions = ReviewDecisionRepository(session)
        self.decisions = DecisionRepository(session)

    @property
    def session(self) -> AsyncSession:
        """The session every bound repository writes through."""
        return self._session

    @property
    def is_committed(self) -> bool:
        """Whether the caller has committed this transaction."""
        return self._committed

    async def flush(self) -> None:
        """Pushes staged writes so foreign keys resolve. Commits nothing."""
        try:
            await self._session.flush()
        except SQLAlchemyError as exc:
            raise PersistenceError(f"Flushing the unit of work failed: {exc}") from exc

    async def commit(self) -> None:
        """Commits the transaction. Called by the transaction owner, never by a repository."""
        try:
            await self._session.commit()
        except SQLAlchemyError as exc:
            raise PersistenceError(f"Committing the unit of work failed: {exc}") from exc
        self._committed = True

    async def rollback(self) -> None:
        """Discards every staged and applied change in this transaction."""
        await self._session.rollback()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Rolls back unless the caller explicitly committed."""
        if not self._committed:
            await self._session.rollback()


@asynccontextmanager
async def unit_of_work() -> AsyncIterator[UnitOfWork]:
    """Opens a Unit of Work over a fresh session and closes it on exit.

    The caller still decides whether the work commits::

        async with unit_of_work() as uow:
            ...
            await uow.commit()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            yield uow
