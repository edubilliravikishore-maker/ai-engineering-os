"""Shared base model and value types for the pure domain layer.

This module deliberately depends on nothing beyond Pydantic and the standard
library. There is no FastAPI, SQLAlchemy, PostgreSQL, filesystem, or network
dependency anywhere in ``ai_engineering_os.domain``.
"""

from datetime import UTC, datetime
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, StringConstraints

__all__ = [
    "DomainModel",
    "NonEmptyText",
    "Sha256Hex",
    "Slug",
    "utc_now",
]

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
"""Text that must carry actual content after whitespace stripping."""

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
"""Lowercase, hyphen-separated stable identifier."""

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
"""Lowercase hexadecimal SHA-256 digest used for evidence integrity."""


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class DomainModel(BaseModel):
    """Base class for all domain entities and value objects.

    Every domain model is frozen. The architecture requires that history is
    additive and never silently overwritten, so a change always produces a new,
    fully revalidated instance rather than mutating an existing record.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    def _evolve(self, **changes: Any) -> Self:
        """Returns a revalidated copy of this model with ``changes`` applied.

        Protected because entities expose explicit, invariant-aware operations
        (``assign``, ``with_status``, ``revise_draft``) instead of arbitrary
        field replacement.
        """
        data = self.model_dump()
        data.update(changes)
        return type(self).model_validate(data)
