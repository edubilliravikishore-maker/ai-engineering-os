"""Work Package repository — the hybrid record (ADR-003 3.5, ADR-005 5.8).

A Work Package is neither purely mutable state nor purely append-only history:

* ``DRAFT`` content remains editable;
* ``SUBMITTED`` is the durable record;
* **submitted content becomes immutable** — enforced here, because only the
  repository can compare what is being written against what is already stored;
* **status is not this repository's authority.** The approved lifecycle
  transitions remain the sole authority for status changes (ADR-003 3.5). This
  repository persists whatever status the caller has already established through
  them; it never decides one, and it never blocks one.
"""

from ai_engineering_os.domain.enums import WorkPackageStatus
from ai_engineering_os.domain.identifiers import TaskRevisionId, WorkPackageId
from ai_engineering_os.domain.work_package import WorkPackage
from ai_engineering_os.storage.errors import AppendOnlyViolationError, NotFoundError
from ai_engineering_os.storage.mappers.work_package import (
    apply_work_package,
    to_domain_work_package,
    to_work_package_row,
)
from ai_engineering_os.storage.models.work_package import (
    WORK_PACKAGE_CONTENT_COLUMNS,
    WorkPackageRow,
)
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["WorkPackageRepository"]


class WorkPackageRepository(BaseRepository[WorkPackageRow]):
    """Reads and writes Work Packages under the hybrid immutability model."""

    row_type = WorkPackageRow
    entity_name = "WorkPackage"

    async def add(self, work_package: WorkPackage) -> None:
        """Records a new Work Package within the caller's transaction."""
        self._stage(to_work_package_row(work_package))
        await self._flush()

    async def get_by_id(self, work_package_id: WorkPackageId) -> WorkPackage:
        """Returns the Work Package recorded under ``work_package_id``."""
        return to_domain_work_package(await self._require_row(work_package_id))

    async def get_by_task_revision(self, task_revision_id: TaskRevisionId) -> WorkPackage:
        """Returns the Work Package recorded against ``task_revision_id``.

        Raises:
            NotFoundError: if that Revision carries no Work Package.
        """
        rows = await self._rows_where(WorkPackageRow.task_revision_id == task_revision_id)
        if not rows:
            raise NotFoundError(
                f"Task Revision {task_revision_id} carries no Work Package",
                entity=self.entity_name,
                entity_id=task_revision_id,
            )
        return to_domain_work_package(rows[0])

    async def save(self, work_package: WorkPackage) -> None:
        """Updates the recorded Work Package under optimistic locking.

        Once the stored row has left ``DRAFT`` its recorded content is frozen: a
        write that would change any content column is rejected. Status may still
        change, because after submission it is an OS projection of the Task
        lifecycle (ADR-003 3.5).

        Raises:
            NotFoundError: if no such Work Package is recorded.
            AppendOnlyViolationError: if submitted content would be rewritten.
            ConcurrencyConflictError: if the record changed since it was read.
        """
        row = await self._require_row(work_package.id)
        if row.status != WorkPackageStatus.DRAFT.value:
            changed = self._content_changes(work_package, row)
            if changed:
                raise AppendOnlyViolationError(
                    f"A {row.status} Work Package cannot have its recorded content rewritten; "
                    "produce a new Revision carrying a new Work Package instead",
                    record_type="WorkPackage",
                    fields=changed,
                )
        await self._save_row(row, lambda target: apply_work_package(work_package, target))

    @staticmethod
    def _content_changes(work_package: WorkPackage, row: WorkPackageRow) -> tuple[str, ...]:
        """Returns the recorded content columns ``work_package`` would change."""
        candidate = to_work_package_row(work_package)
        return tuple(
            column
            for column in WORK_PACKAGE_CONTENT_COLUMNS
            if getattr(candidate, column) != getattr(row, column)
        )
