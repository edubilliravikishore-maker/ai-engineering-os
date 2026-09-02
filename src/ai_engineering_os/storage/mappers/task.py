"""Task, Task dependency, and Task Revision <-> row mapping.

A Task Revision row carries **no status** (ADR-003 3.1), so nothing about
active-ness is read from or written to it. ``TaskRevisionHistory`` is assembled
by the repository from ordered revision rows; it is a derived aggregate and has
no table of its own.
"""

from collections.abc import Sequence

from ai_engineering_os.domain.task import Task, TaskRevision, TaskRevisionHistory
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.task import TaskDependencyRow, TaskRevisionRow, TaskRow

__all__ = [
    "apply_task",
    "to_domain_revision",
    "to_domain_revision_history",
    "to_domain_task",
    "to_revision_row",
    "to_task_dependency_rows",
    "to_task_row",
]


def to_domain_task(row: TaskRow, dependencies: Sequence[TaskDependencyRow]) -> Task:
    """Rebuilds the domain Task recorded by ``row`` and its dependency edges."""
    ordered = sorted(dependencies, key=lambda edge: edge.position)
    return reconstruct(
        Task,
        {
            "id": row.id,
            "feature_id": row.feature_id,
            "feature_plan_id": row.feature_plan_id,
            "plan_definition_key": row.plan_definition_key,
            "title": row.title,
            "capability": row.capability,
            "status": row.status,
            "assigned_worker_id": row.assigned_worker_id,
            "dependencies": [edge.depends_on_task_id for edge in ordered],
            "active_revision_number": row.active_revision_number,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        },
        entity_id=row.id,
    )


def apply_task(task: Task, row: TaskRow) -> None:
    """Writes the Task's own columns onto ``row``.

    Dependency edges are child rows fixed at creation; the Task lifecycle never
    rewrites them, so they are not written here.
    """
    row.feature_id = task.feature_id
    row.feature_plan_id = task.feature_plan_id
    row.plan_definition_key = task.plan_definition_key
    row.title = task.title
    row.capability = task.capability.value
    row.status = task.status.value
    row.assigned_worker_id = task.assigned_worker_id
    row.active_revision_number = task.active_revision_number
    row.created_at = task.created_at
    row.updated_at = task.updated_at


def to_task_row(task: Task) -> TaskRow:
    """Builds a new row for ``task``."""
    row = TaskRow(id=task.id, version=1)
    apply_task(task, row)
    return row


def to_task_dependency_rows(task: Task) -> list[TaskDependencyRow]:
    """Builds the child rows recording ``task``'s prerequisites, in order."""
    return [
        TaskDependencyRow(task_id=task.id, depends_on_task_id=dependency, position=position)
        for position, dependency in enumerate(task.dependencies)
    ]


def to_domain_revision(row: TaskRevisionRow) -> TaskRevision:
    """Rebuilds the immutable Task Revision recorded by ``row``."""
    return reconstruct(
        TaskRevision,
        {
            "id": row.id,
            "task_id": row.task_id,
            "revision_number": row.revision_number,
            "created_by_worker_id": row.created_by_worker_id,
            "work_package_id": row.work_package_id,
            "review_decision_id": row.review_decision_id,
            "qa_report_id": row.qa_report_id,
            "created_at": row.created_at,
        },
        entity_id=row.id,
    )


def to_revision_row(revision: TaskRevision) -> TaskRevisionRow:
    """Builds the append-only row recording ``revision``."""
    return TaskRevisionRow(
        id=revision.id,
        task_id=revision.task_id,
        revision_number=revision.revision_number,
        created_by_worker_id=revision.created_by_worker_id,
        work_package_id=revision.work_package_id,
        review_decision_id=revision.review_decision_id,
        qa_report_id=revision.qa_report_id,
        created_at=revision.created_at,
    )


def to_domain_revision_history(
    task_id: object, rows: Sequence[TaskRevisionRow]
) -> TaskRevisionHistory:
    """Assembles the additive Revision history of one Task from ordered rows."""
    ordered = sorted(rows, key=lambda row: row.revision_number)
    return reconstruct(
        TaskRevisionHistory,
        {
            "task_id": task_id,
            "revisions": [to_domain_revision(row).model_dump() for row in ordered],
        },
        entity_id=str(task_id),
    )
