"""Task, Task Revision, and additive revision history (Blueprint 4.1 #3-#4).

Design Session 006: a Task has one identity and evolves through Revisions.
History is never rewritten and only one Revision is active at a time.
"""

from collections.abc import Sequence
from datetime import datetime

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, Slug, utc_now
from ai_engineering_os.domain.enums import CapabilityType, TaskStatus
from ai_engineering_os.domain.errors import ImmutableRecordError, RevisionSequenceError
from ai_engineering_os.domain.identifiers import (
    ActorId,
    FeatureId,
    FeaturePlanId,
    QAReportId,
    ReviewDecisionId,
    TaskId,
    TaskRevisionId,
    WorkPackageId,
)

__all__ = [
    "ASSIGNMENT_REQUIRED_STATUSES",
    "work_authors",
    "REVIEWER_REQUIRED_STATUSES",
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

REVIEWER_REQUIRED_STATUSES: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.IN_REVIEW,
        TaskStatus.IN_QA,
        TaskStatus.REVISION_REQUIRED,
        TaskStatus.ACCEPTED,
    }
)
"""Statuses only reachable once a Reviewer has been routed the Task (ADR-007 7.3).

``REVISION_REQUIRED`` is included because both edges into it leave a review or a
QA pass that a Reviewer had already been routed. ``IN_PROGRESS`` is **not**: a
Task re-entering it on a new Revision keeps the Reviewer it already has, so the
field is not required there and is never cleared.
"""


class Task(DomainModel):
    """The smallest unit of work assigned to exactly one Worker.

    Every Task is traceable to the planning record that produced it
    (ADR-003 3.12, ADR-004 4.8)::

        Task -> Feature Plan -> plan-local Task Definition

    ``feature_plan_id`` and ``plan_definition_key`` are both **required**.
    Without the link the OS cannot evaluate the originating plan's status, and
    the ``ORIGINATING_PLAN_ACTIVE`` gate on ``-> READY`` would be unenforceable.
    Existence still confers no execution authority: a Task created under a
    ``DRAFT`` plan is a planning record until the plan is ``ACTIVE``.
    """

    id: TaskId
    feature_id: FeatureId
    feature_plan_id: FeaturePlanId
    plan_definition_key: Slug
    title: NonEmptyText
    capability: CapabilityType
    status: TaskStatus = TaskStatus.CREATED
    assigned_worker_id: ActorId | None = None
    reviewer_id: ActorId | None = None
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
    def _review_routing_must_match_status(self) -> "Task":
        """A Task under review or past it records the Reviewer routed to it.

        ADR-007 7.3. The Reviewer is recorded at routing, so a Task that has not
        yet been worked on cannot carry one, and a Task from ``IN_REVIEW``
        onwards must.
        """
        if self.status in UNASSIGNED_STATUSES and self.reviewer_id is not None:
            raise ValueError(f"A Task in status {self.status} cannot record a Reviewer")
        if self.status in REVIEWER_REQUIRED_STATUSES and self.reviewer_id is None:
            raise ValueError(f"A Task in status {self.status} must record a Reviewer")
        return self

    @model_validator(mode="after")
    def _reviewer_is_never_the_worker(self) -> "Task":
        """The Worker who did the work never reviews it (ADR-001, ADR-007 7.3).

        Enforced here as well as by the Rule Engine on purpose. The rule refuses
        the transition that would route it; this makes the state **unconstructible**,
        so no other path — a mapper, a repository, a future caller — can produce a
        Task that violates ADR-001. Full eligibility still belongs to the rule:
        this model cannot see the Task's Revisions and so cannot check authorship.
        """
        if (
            self.reviewer_id is not None
            and self.assigned_worker_id is not None
            and self.reviewer_id == self.assigned_worker_id
        ):
            raise ValueError("A Task's Reviewer cannot be the Worker assigned to it")
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

    def routed_to_reviewer(self, reviewer_id: ActorId, *, at: datetime | None = None) -> "Task":
        """Returns a new IN_REVIEW Task routed to ``reviewer_id``.

        Routing and the status change are **one operation** so a Task can never
        be left recorded as under review with no Reviewer, or carrying a Reviewer
        it was never routed to. Every invariant above revalidates, including the
        refusal to record the assigned Worker as the Reviewer.
        """
        return self._evolve(
            status=TaskStatus.IN_REVIEW,
            reviewer_id=reviewer_id,
            updated_at=at or utc_now(),
        )

    def is_reviewed_by(self, actor_id: ActorId) -> bool:
        """Returns whether ``actor_id`` is the Reviewer routed this Task."""
        return self.reviewer_id is not None and self.reviewer_id == actor_id

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


def work_authors(task: Task, revisions: Sequence[TaskRevision]) -> frozenset[ActorId]:
    """Returns every Actor who performed work on ``task``.

    The assigned Worker **and** the author of every Revision. A Task can change
    hands, so the current assignment alone is not the whole answer: an Actor who
    authored an earlier Revision worked on this Task whether or not they are
    still assigned to it.

    This lives in the domain layer because two layers that may not import each
    other both need it and must agree. ``core`` routes a Task away from its
    authors; ``rules`` refuses the transition if it was not. If each computed
    "who worked on this" separately, the router and the rule could disagree, and
    the disagreement would surface as a Task that can be routed but never
    reviewed.
    """
    authors = {
        revision.created_by_worker_id for revision in revisions if revision.task_id == task.id
    }
    if task.assigned_worker_id is not None:
        authors.add(task.assigned_worker_id)
    return frozenset(authors)
