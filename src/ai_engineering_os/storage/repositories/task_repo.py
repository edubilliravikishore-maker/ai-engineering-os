"""Task repository (ADR-005 5.4).

``get_many_by_id`` exists because a real consumer needs it: the ``referenced_tasks``
fact of the approved seven-fact ``RuleContext`` (ADR-004 4.4) resolves a list of
Task identifiers, and resolving them one at a time would be a query per
dependency. Bulk reads are earned by a use case, never offered generically
(ADR-005 5.4, Q22).
"""

from collections.abc import Sequence

from sqlalchemy import select

from ai_engineering_os.domain.identifiers import FeatureId, TaskId
from ai_engineering_os.domain.task import Task
from ai_engineering_os.storage.mappers.task import (
    apply_task,
    to_domain_task,
    to_task_dependency_rows,
    to_task_row,
)
from ai_engineering_os.storage.models.task import TaskDependencyRow, TaskRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["TaskRepository"]


class TaskRepository(BaseRepository[TaskRow]):
    """Reads and writes Tasks and their prerequisite edges."""

    row_type = TaskRow
    entity_name = "Task"

    async def add(self, task: Task) -> None:
        """Records a new Task and its declared dependencies."""
        self._stage(to_task_row(task))
        await self._flush()
        for edge in to_task_dependency_rows(task):
            self._session.add(edge)
        await self._flush()

    async def get_by_id(self, task_id: TaskId) -> Task:
        """Returns the Task recorded under ``task_id``, with its dependencies."""
        row = await self._require_row(task_id)
        edges = await self._dependency_map([task_id])
        return to_domain_task(row, edges.get(row.id, []))

    async def get_many_by_id(self, task_ids: Sequence[TaskId]) -> tuple[Task, ...]:
        """Returns the Tasks recorded under ``task_ids``, in the order requested.

        Identifiers with no recorded Task are omitted rather than raising: the
        caller asked which of these exist, not for a guarantee that all do.
        """
        if not task_ids:
            return ()
        rows = await self._rows_where(TaskRow.id.in_(list(task_ids)))
        edges = await self._dependency_map([TaskId(row.id) for row in rows])
        by_id = {row.id: to_domain_task(row, edges.get(row.id, [])) for row in rows}
        return tuple(by_id[task_id] for task_id in task_ids if task_id in by_id)

    async def list_by_feature(self, feature_id: FeatureId) -> tuple[Task, ...]:
        """Returns every Task recorded against ``feature_id``.

        Ordered by the domain's own ``created_at``, never by a persistence
        metadata column (ADR-005 5.9).
        """
        rows = await self._rows_where(TaskRow.feature_id == feature_id, order_by=TaskRow.created_at)
        edges = await self._dependency_map([TaskId(row.id) for row in rows])
        return tuple(to_domain_task(row, edges.get(row.id, [])) for row in rows)

    async def save(self, task: Task) -> None:
        """Updates the recorded Task under optimistic locking.

        Dependency edges are fixed at creation and are not rewritten here.
        """
        row = await self._require_row(task.id)
        await self._save_row(row, lambda target: apply_task(task, target))

    async def _dependency_map(
        self, task_ids: Sequence[TaskId]
    ) -> dict[object, list[TaskDependencyRow]]:
        """Returns the prerequisite edges of ``task_ids``, grouped and ordered."""
        if not task_ids:
            return {}
        statement = (
            select(TaskDependencyRow)
            .where(TaskDependencyRow.task_id.in_(list(task_ids)))
            .order_by(TaskDependencyRow.position)
        )
        with self._translating():
            result = await self._session.execute(statement)
        grouped: dict[object, list[TaskDependencyRow]] = {}
        for edge in result.scalars().all():
            grouped.setdefault(edge.task_id, []).append(edge)
        return grouped
