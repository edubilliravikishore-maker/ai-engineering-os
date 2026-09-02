"""Shared mapping mechanics between stored rows and domain objects.

Two rules govern every mapper in this package:

1. **Reconstruction validates** (ADR-005 5.3). A domain object is rebuilt through
   ``model_validate``, so every domain invariant re-runs on load. A stored row
   that no longer forms a valid domain object raises
   :class:`DomainReconstructionError`. **Nothing is silently repaired**, because
   silent repair would let an invalid state re-enter the system through
   persistence — which ADR-002's testing principles require to be unreachable.
2. **Persistence metadata is never read** (ADR-005 5.9). ``row_created_at`` and
   ``row_updated_at`` exist on the tables and are deliberately absent from every
   mapper. They are metadata about storage, not facts about the domain.
"""

from typing import Any
from uuid import UUID

from pydantic import ValidationError

from ai_engineering_os.domain.base import DomainModel
from ai_engineering_os.storage.errors import DomainReconstructionError

__all__ = ["reconstruct"]


def reconstruct[ModelT: DomainModel](
    model: type[ModelT],
    data: dict[str, Any],
    *,
    entity_id: UUID | str | None = None,
) -> ModelT:
    """Rebuilds a domain object from stored data, failing loudly on invalid input.

    Raises:
        DomainReconstructionError: if ``data`` does not satisfy the domain
            model's invariants. The original ``ValidationError`` is chained, so
            the offending field is never lost.
    """
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise DomainReconstructionError(
            f"Stored data does not form a valid {model.__name__}: {exc}",
            entity=model.__name__,
            entity_id=entity_id,
        ) from exc
