"""Task, Task Revision, and additive revision history (Blueprint 4.1 #3-#4).

Design Session 006: a Task has one identity and evolves through Revisions.
History is never rewritten and only one Revision is active at a time.
"""

from datetime import datetime

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, utc_now
from ai_engineering_os.domain.enums import CapabilityType, TaskStatus
from ai_engineering_os.domain.errors import ImmutableRecordError, RevisionSequenceError
from ai_engineering_os.domain.identifiers import (
    ActorId,
    FeatureId,
    QAReportId,
    ReviewDecisionId,
    TaskId,
    TaskRevisionId,
    WorkPackageId,
)

__all__ = [
    "ASSIGNMENT_REQUIRED_STATUSES",
    "REVISION_REQUIRED_STATUSES",
    "UNASSIGNED_STATUSES",
    "Task",
    "TaskRevision",
    "TaskRevisionHistory",
]

UNASSIGNED_STATUSES: frozenset[TaskStatus] = frozenset(
    {TaskStatus.CREATED, TaskStatus.PENDING_DEPENDENCIES, TaskStatus.READY}
)
"""Statuses that precede assignment; no Worker may be recorded yet."""

ASSIGNMENT_REQUIRED_STATUSES: frozenset[TaskStatus] = frozenset(TaskStatus) - UNASSIGNED_STATUSES
"""Statuses from ASSIGNED onwards; a Worker must be recorded."""

REVISION_REQUIRED_STATUSES: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.SUBMITTED,
        TaskStatus.IN_REVIEW,
        TaskStatus.IN_QA,
        TaskStatus.REVISION_REQUIRED,
        TaskStatus.ACCEPTED,
    }
)
"""Statuses only reachable after a Worker has submitted a Revision."""


class Task(DomainModel):
    """The smallest unit of work assigned to exactly one Worker."""

    id: TaskId
    feature_id: FeatureId
    title: NonEmptyText
    capability: CapabilityType
    status: TaskStatus = TaskStatus.CREATED
    assigned_worker_id: ActorId | None = None
    dependencies: tuple[TaskId, ...] = ()
    active_revision_number: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _dependencies_must_be_well_formed(self) -> "Task":
        if self.id in self.dependencies:
            raise ValueError("A Task cannot depend on itself")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("A Task cannot declare duplicate dependencies")
        return self

    @model_validator(mode="after")
    def _pending_dependencies_requires_dependencies(self) -> "Task":
        """Blueprint 5.2 rejects PENDING_DEPENDENCIES when no dependency is declared."""
        if self.status is TaskStatus.PENDING_DEPENDENCIES and not self.dependencies:
            raise ValueError("A PENDING_DEPENDENCIES Task must declare at least one dependency")
        return self

    @model_validator(mode="after")
    def _assignment_must_match_status(self) -> "Task":
        if self.status in UNASSIGNED_STATUSES and self.assigned_worker_id is not None:
            raise ValueError(f"A Task in status {self.status} cannot record an assigned Worker")
        if self.status in ASSIGNMENT_REQUIRED_STATUSES and self.assigned_worker_id is None:
            raise ValueError(f"A Task in status {self.status} must record an assigned Worker")
        return self

    @model_validator(mode="after")
    def _post_submission_requires_revision(self) -> "Task":
        if self.status in REVISION_REQUIRED_STATUSES and self.active_revision_number < 1:
            raise ValueError(f"A Task in status {self.status} must have an active Revision")
        return self

    @model_validator(mode="after")
    def _timestamps_must_be_ordered(self) -> "Task":
        if self.updated_at < self.created_at:
            raise ValueError("Task updated_at cannot precede created_at")
        return self

    def with_status(self, status: TaskStatus, *, at: datetime | None = None) -> "Task":
        """Returns a new Task carrying ``status``, revalidating every invariant."""
        return self._evolve(status=status, updated_at=at or utc_now())

    def assign(self, worker_id: ActorId, *, at: datetime | None = None) -> "Task":
        """Returns a new ASSIGNED Task bound to ``worker_id``."""
        return self._evolve(
            status=TaskStatus.ASSIGNED,
            assigned_worker_id=worker_id,
            updated_at=at or utc_now(),
        )

    def with_active_revision(self, revision_number: int, *, at: datetime | None = None) -> "Task":
        """Returns a new Task pointing at ``revision_number`` as the active Revision."""
        if revision_number <= self.active_revision_number:
            raise RevisionSequenceError(
                "Task active revision number must strictly increase",
                expected_revision_number=self.active_revision_number + 1,
                received_revision_number=revision_number,
            )
        return self._evolve(active_revision_number=revision_number, updated_at=at or utc_now())

    def is_assigned_to(self, actor_id: ActorId) -> bool:
        """Returns whether ``actor_id`` is the Worker recorded on this Task."""
        return self.assigned_worker_id is not None and self.assigned_worker_id == actor_id


class TaskRevision(DomainModel):
    """One immutable Revision of a Task.

    A Revision is an append-only historical record. It is never edited, re-marked,
    or replaced; corrections are expressed as the next Revision.

    A Revision carries no active/superseded marker. Per ADR-003, the authoritative
    active-revision pointer is ``Task.active_revision_number``, so active-ness is
    derived rather than stored. Storing it would require writing to an already
    recorded Revision.
    """

    id: TaskRevisionId
    task_id: TaskId
    revision_number: int = Field(ge=1)
    created_by_worker_id: ActorId
    work_package_id: WorkPackageId | None = None
    review_decision_id: ReviewDecisionId | None = None
    qa_report_id: QAReportId | None = None
    created_at: datetime = Field(default_factory=utc_now)


class TaskRevisionHistory(DomainModel):
    """The complete, strictly additive Revision history of one Task."""

    task_id: TaskId
    revisions: tuple[TaskRevision, ...] = ()

    @model_validator(mode="after")
    def _revisions_must_belong_to_task(self) -> "TaskRevisionHistory":
        foreign = [r.revision_number for r in self.revisions if r.task_id != self.task_id]
        if foreign:
            raise ValueError(f"Revision history contains revisions of another Task: {foreign}")
        return self

    @model_validator(mode="after")
    def _revision_numbers_must_be_contiguous(self) -> "TaskRevisionHistory":
        expected = list(range(1, len(self.revisions) + 1))
        actual = [r.revision_number for r in self.revisions]
        if actual != expected:
            raise ValueError(
                f"Revision history must be contiguous and ordered; expected {expected}, got {actual}"
            )
        return self

    @property
    def next_revision_number(self) -> int:
        """The revision number the next Revision must carry."""
        return len(self.revisions) + 1

    @property
    def active_revision(self) -> TaskRevision | None:
        """The head of the history, which is the active Revision.

        Design Session 006 requires that only one Revision is active at a time.
        That is satisfied by derivation: the head of a contiguous, append-only
        history is the active Revision. ``Task.active_revision_number`` remains
        the authoritative pointer (ADR-003).
        """
        return self.revisions[-1] if self.revisions else None

    def is_consistent_with(self, task: Task) -> bool:
        """Returns whether this history agrees with the Task's active pointer."""
        return task.id == self.task_id and task.active_revision_number == len(self.revisions)

    def revision(self, revision_number: int) -> TaskRevision | None:
        """Returns the Revision recorded under ``revision_number``, if any."""
        return next((r for r in self.revisions if r.revision_number == revision_number), None)

    def append(self, revision: TaskRevision) -> "TaskRevisionHistory":
        """Returns a new history with ``revision`` appended.

        Every previously recorded Revision is carried through untouched. No
        recorded Revision is rewritten, re-marked, or removed.
        """
        if revision.task_id != self.task_id:
            raise ImmutableRecordError(
                "A Revision cannot be appended to another Task's history",
                record_type="TaskRevisionHistory",
                operation="append",
            )
        if revision.revision_number != self.next_revision_number:
            raise RevisionSequenceError(
                "Task Revisions are strictly additive and must increment by one",
                expected_revision_number=self.next_revision_number,
                received_revision_number=revision.revision_number,
            )
        return TaskRevisionHistory(
            task_id=self.task_id,
            revisions=(*self.revisions, revision),
        )
