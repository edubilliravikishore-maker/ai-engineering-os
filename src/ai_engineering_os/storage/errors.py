"""Persistence exceptions for AI Engineering OS (ADR-005 5.12).

The repository **translates** infrastructure and database failures into these
application-level signals. A caller never sees a ``sqlalchemy`` exception, just
as it never sees a SQLAlchemy model (ADR-005 5.11) — otherwise the storage
boundary would leak through the exception path instead of the return path.

This hierarchy is deliberately **separate from** ``domain.errors``. That module
records that its errors "intentionally carry no HTTP status codes, transport
concerns, or persistence concerns", so a persistence failure does not belong in
it. These errors likewise carry **no HTTP status codes**: mapping them onto a
transport is Checkpoint 7's concern.

The repository reports the problem. The service/use-case layer decides what the
business response should be (ADR-005 5.5, 5.12).
"""

from typing import ClassVar
from uuid import UUID

__all__ = [
    "AppendOnlyViolationError",
    "ConcurrencyConflictError",
    "DomainReconstructionError",
    "IntegrityConstraintError",
    "NotFoundError",
    "PersistenceError",
]


class PersistenceError(Exception):
    """Base class for every AI Engineering OS persistence failure."""

    code: ClassVar[str] = "PERSISTENCE_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class NotFoundError(PersistenceError):
    """Raised when a requested record does not exist (ADR-005 5.12, Q21).

    Deliberately specific rather than folded into :class:`PersistenceError`: a
    missing record is an ordinary outcome a caller may reasonably act on, while
    the base class signals that persistence itself misbehaved.
    """

    code: ClassVar[str] = "NOT_FOUND"

    def __init__(self, message: str, *, entity: str, entity_id: UUID | str) -> None:
        super().__init__(message)
        self.entity = entity
        self.entity_id = entity_id


class ConcurrencyConflictError(PersistenceError):
    """Raised when a concurrent modification was detected (ADR-005 5.6).

    The write did not happen and nothing was overwritten. The record changed
    between the read that produced the in-hand domain object and this write, so
    the caller must re-read and decide again rather than have its stale view win
    by arrival order.
    """

    code: ClassVar[str] = "CONCURRENCY_CONFLICT"

    def __init__(self, message: str, *, entity: str, entity_id: UUID | str) -> None:
        super().__init__(message)
        self.entity = entity
        self.entity_id = entity_id


class IntegrityConstraintError(PersistenceError):
    """Raised when the database rejected a write on a fundamental integrity rule.

    Foreign key, unique, not-null, and check constraint violations (ADR-005
    5.14). Business and state-machine rules are **not** enforced here; they live
    in ``domain``, ``state``, and ``rules``.
    """

    code: ClassVar[str] = "INTEGRITY_CONSTRAINT"

    def __init__(self, message: str, *, constraint: str | None = None) -> None:
        super().__init__(message)
        self.constraint = constraint


class AppendOnlyViolationError(PersistenceError):
    """Raised when a write would rewrite an architecturally immutable record.

    Append-only storage is enforced primarily **by construction**: an append-only
    repository exposes no update method at all (ADR-005 5.4, 5.8). This error
    covers the one case construction cannot express — a hybrid record whose
    status may still change while its recorded content may not, which is exactly
    the Work Package after submission (ADR-003 3.5, ADR-005 5.8).
    """

    code: ClassVar[str] = "APPEND_ONLY_VIOLATION"

    def __init__(self, message: str, *, record_type: str, fields: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.record_type = record_type
        self.fields = fields


class DomainReconstructionError(PersistenceError):
    """Raised when a stored row cannot form a valid domain object (ADR-005 5.3).

    The repository **fails** rather than returning an invalid domain object or
    silently repairing one. Silent repair would let an invalid state re-enter the
    system through persistence, which ADR-002's testing principles require to be
    unreachable through normal OS interfaces.
    """

    code: ClassVar[str] = "DOMAIN_RECONSTRUCTION"

    def __init__(self, message: str, *, entity: str, entity_id: UUID | str | None = None) -> None:
        super().__init__(message)
        self.entity = entity
        self.entity_id = entity_id
