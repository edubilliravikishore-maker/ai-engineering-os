"""Shared column conventions for the AI Engineering OS relational schema.

Three conventions live here, each traceable to a recorded decision:

* **Persistence metadata timestamps** (ADR-005 5.9). ``row_created_at`` and
  ``row_updated_at`` are **database-generated** and record when a row physically
  landed. They are **metadata only**: no mapper reads them, no domain model
  gains a field for them, and no repository orders or filters by them. The
  domain's own timestamps — ``Feature.created_at``, ``QAReport.created_at`` and
  the rest — remain domain-owned and are persisted exactly as produced.
* **Statuses as ``VARCHAR`` with a ``CHECK``** (ADR-005 5.14), never a native
  PostgreSQL ``ENUM``. Deferred states are expected to be added later, and
  extending a ``CHECK`` is one migration statement where ``ALTER TYPE`` is not.
  **No deferred state is admitted by any constraint here.**
* **Ordered child collections carry ``position``.** Several domain collections
  are ordered tuples. ``position`` preserves that order across a round trip; it
  is a persistence mechanism and carries no domain meaning.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

__all__ = [
    "POSITION",
    "RowMetadataMixin",
    "status_check",
    "status_column",
]

POSITION = "position"
"""Column name preserving the order of an ordered domain collection."""


class RowMetadataMixin:
    """Database-generated persistence metadata (ADR-005 5.9).

    Never mapped into a domain object, and never used for ordering, filtering,
    or authoritative QA-result selection (ADR-004 4.15).
    """

    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def status_column(*, nullable: bool = False) -> Mapped[str]:
    """Returns the column used for every lifecycle status and enumerated label."""
    return mapped_column(String(64), nullable=nullable)


def status_check(column: str, values: type[StrEnum], *, name: str) -> CheckConstraint:
    """Returns a ``CHECK`` constraint admitting exactly the members of ``values``.

    Generated from the enumeration rather than hand-listed, so a constraint
    cannot drift from the vocabulary the domain layer owns.
    """
    admitted = ", ".join(f"'{member.value}'" for member in values)
    return CheckConstraint(f"{column} IN ({admitted})", name=name)


def version_column() -> Mapped[int]:
    """Returns the optimistic-lock version column (ADR-005 5.6).

    Present on authoritative-state tables only. An append-only table carries no
    version, because a row that is never updated cannot lose an update race.
    """
    return mapped_column(Integer, nullable=False)
