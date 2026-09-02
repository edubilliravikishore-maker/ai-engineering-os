"""Task Revision repository — append-only (ADR-003 3.1, ADR-005 5.8).

**There is no update method.** A Revision is never rewritten or re-marked, and
append-only storage is enforced by construction: no code path capable of
updating this table exists (ADR-005 5.4, 5.8).

``TaskRevisionHistory`` is assembled here from ordered rows. It is a derived
aggregate with no table of its own, and the head of the contiguous history is the
active Revision by derivation — ``Task.active_revision_number`` remains the
authoritative pointer.
"""

from ai_engineering_os.domain.identifiers import TaskId, TaskRevisionId
from ai_engineering_os.domain.task import TaskRevision, TaskRevisionHistory
from ai_engineering_os.storage.mappers.task import (
    to_domain_revision,
    to_domain_revision_history,
    to_revision_row,
)
from ai_engineering_os.storage.models.task import TaskRevisionRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["TaskRevisionRepository"]


class TaskRevisionRepository(BaseRepository[TaskRevisionRow]):
    """Appends and reads immutable Task Revisions."""

    row_type = TaskRevisionRow
    entity_name = "TaskRevision"

    async def add(self, revision: TaskRevision) -> None:
        """Appends a Revision. Nothing already recorded is touched."""
        self._stage(to_revision_row(revision))
        await self._flush()

    async def get_by_id(self, revision_id: TaskRevisionId) -> TaskRevision:
        """Returns the Revision recorded under ``revision_id``."""
        return to_domain_revision(await self._require_row(revision_id))

    async def get_history(self, task_id: TaskId) -> TaskRevisionHistory:
        """Returns the complete additive Revision history of ``task_id``.

        Ordered by ``revision_number`` — the domain's own sequence, never a
        persistence metadata timestamp (ADR-005 5.9).
        """
        rows = await self._rows_where(
            TaskRevisionRow.task_id == task_id, order_by=TaskRevisionRow.revision_number
        )
        return to_domain_revision_history(task_id, rows)
