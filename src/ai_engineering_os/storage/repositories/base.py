"""Reusable persistence mechanics (ADR-005 5.4).

This base carries **only** what every repository genuinely shares. Everything
here is **protected**: a generic CRUD surface is not exposed merely because a
generic base exists (ADR-005 5.4, Q16). Each domain repository publishes its own
explicitly named, typed operations, so a caller cannot reach for an operation the
domain never sanctioned.

What this base deliberately does **not** provide:

* **No ``delete``.** There is no generic delete capability anywhere in the OS
  (ADR-005 5.7). Removal semantics must be explicitly designed by the domain if
  ever needed, and the capability does not exist to be called by accident.
* **No ``commit`` or ``rollback``.** The service/use-case layer owns the
  transaction boundary (ADR-005 5.5). A repository that committed would let a
  partially applied transition reach durable storage.
* **No ``update``** on the base. Only the mutable repositories expose a save
  operation; an append-only repository has no update method at all, which is how
  append-only storage is enforced by construction (ADR-005 5.8).
"""

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.errors import (
    ConcurrencyConflictError,
    IntegrityConstraintError,
    NotFoundError,
    PersistenceError,
)

__all__ = ["BaseRepository"]


class BaseRepository[RowT: Base]:
    """Shared mechanics over one table. Subclasses publish the domain operations."""

    row_type: type[RowT]
    entity_name: str

    def __init__(self, session: AsyncSession) -> None:
        """Binds the repository to the session supplied by the transaction owner.

        The repository never creates a session and never closes one: the
        service/use-case layer owns the boundary (ADR-005 5.5).
        """
        self._session = session
        self._loaded: dict[UUID, RowT] = {}

    # -- protected mechanics ------------------------------------------------

    def _track(self, row: RowT) -> RowT:
        """Retains ``row`` for the lifetime of the transaction.

        **This is load-bearing for optimistic locking and must not be removed.**
        SQLAlchemy's identity map holds *weak* references. Because a repository
        returns a domain object and keeps no reference to the row it was built
        from, an untracked row is garbage-collected almost immediately; the next
        ``session.get`` then re-reads it and picks up whatever version another
        transaction has since committed. The stale-version check would still run,
        but always against a freshly read version — silently degrading ADR-005
        5.6 to last-write-wins.

        Holding a strong reference keeps the version read at load time as the
        token the eventual ``UPDATE`` matches on. The map is bounded by the
        transaction and discarded with the repository.
        """
        identity = row.__dict__.get("id")
        if isinstance(identity, UUID):
            self._loaded.setdefault(identity, row)
        return row

    def _stage(self, row: RowT) -> None:
        """Stages ``row`` for insertion within the caller's transaction."""
        self._session.add(row)
        self._track(row)

    async def _flush(self) -> None:
        """Pushes staged writes so foreign keys resolve. Commits nothing."""
        with self._translating():
            await self._session.flush()

    async def _get_row(self, entity_id: UUID) -> RowT | None:
        """Returns the row identified by ``entity_id``, or None.

        A row already loaded in this transaction is returned as loaded, so the
        version it was read at remains the optimistic-lock token (see
        :meth:`_track`).
        """
        tracked = self._loaded.get(entity_id)
        if tracked is not None:
            return tracked
        with self._translating():
            row = await self._session.get(self.row_type, entity_id)
        return self._track(row) if row is not None else None

    async def _require_row(self, entity_id: UUID) -> RowT:
        """Returns the row identified by ``entity_id``, failing closed if absent."""
        row = await self._get_row(entity_id)
        if row is None:
            raise NotFoundError(
                f"No {self.entity_name} is recorded under {entity_id}",
                entity=self.entity_name,
                entity_id=entity_id,
            )
        return row

    async def _rows_where(self, *criteria: Any, order_by: Any = None) -> Sequence[RowT]:
        """Returns every row matching ``criteria``.

        ``order_by`` never accepts a persistence metadata column: ADR-005 5.9
        forbids ordering or filtering by ``row_created_at`` / ``row_updated_at``.
        """
        statement = select(self.row_type).where(*criteria)
        if order_by is not None:
            statement = statement.order_by(order_by)
        with self._translating():
            result = await self._session.execute(statement)
        return [self._track(row) for row in result.scalars().all()]

    async def _save_row(self, row: RowT, mutate: Callable[[RowT], None]) -> None:
        """Applies ``mutate`` to ``row`` and flushes under optimistic locking.

        The ``UPDATE`` matches on the version read when the row was loaded. If
        another transaction changed the record in between, no row matches and a
        :class:`ConcurrencyConflictError` is raised. Nothing is silently
        overwritten (ADR-005 5.6).
        """
        mutate(row)
        try:
            await self._session.flush()
        except StaleDataError as exc:
            raise ConcurrencyConflictError(
                f"The {self.entity_name} {row.__dict__.get('id')} changed since it was read",
                entity=self.entity_name,
                entity_id=str(row.__dict__.get("id")),
            ) from exc
        except IntegrityError as exc:
            raise _integrity_error(exc) from exc
        except SQLAlchemyError as exc:
            raise PersistenceError(f"Persisting the {self.entity_name} failed: {exc}") from exc

    @contextmanager
    def _translating(self) -> Iterator[None]:
        """Translates infrastructure failures raised inside the block (ADR-005 5.12).

        A context manager rather than a wrapper around the awaitable: wrapping
        erases the awaited type, and a repository that returns ``Any`` would let
        an ORM row escape the boundary unnoticed (ADR-005 5.11).
        """
        try:
            yield
        except IntegrityError as exc:
            raise _integrity_error(exc) from exc
        except StaleDataError as exc:
            raise ConcurrencyConflictError(
                f"A concurrent modification of {self.entity_name} was detected",
                entity=self.entity_name,
                entity_id="unknown",
            ) from exc
        except SQLAlchemyError as exc:
            raise PersistenceError(
                f"A {self.entity_name} persistence operation failed: {exc}"
            ) from exc


def _integrity_error(exc: IntegrityError) -> IntegrityConstraintError:
    """Builds the translated form of a database integrity violation."""
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    return IntegrityConstraintError(
        f"The database rejected the write on a data integrity rule: {exc.orig}",
        constraint=constraint,
    )
