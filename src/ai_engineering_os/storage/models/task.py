"""Task, Task dependency, and Task Revision tables (Blueprint 4.1 #3, #4).

``tasks`` is authoritative current state. ``task_revisions`` is **append-only
history** and, per ADR-003 3.1, carries **no status column and no version
column**: a Revision is never rewritten or re-marked, and the authoritative
active-revision pointer lives on ``tasks.active_revision_number``.

``task_dependencies`` is a child table (ADR-005 5.2) because
``DependenciesAcceptedRule`` inspects each dependency's status, and each entry is
a real reference to another Task.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import CapabilityType, TaskStatus
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import (
    RowMetadataMixin,
    status_check,
    status_column,
    version_column,
)

__all__ = ["TaskDependencyRow", "TaskRevisionRow", "TaskRow"]


class TaskRow(RowMetadataMixin, Base):
    """The smallest unit of work assigned to exactly one Worker.

    ``feature_plan_id`` and ``plan_definition_key`` are both **NOT NULL**
    (ADR-003 3.12, ADR-004 4.8). Without them the originating plan cannot be
    evaluated and the ``ORIGINATING_PLAN_ACTIVE`` gate would be unenforceable.
    """

    __tablename__ = "tasks"
    __table_args__ = (
        status_check("status", TaskStatus, name="ck_tasks_status"),
        status_check("capability", CapabilityType, name="ck_tasks_capability"),
        CheckConstraint("active_revision_number >= 0", name="ck_tasks_active_revision_number"),
        CheckConstraint("updated_at >= created_at", name="ck_tasks_timestamp_order"),
        # ADR-001, ADR-007 7.3: the Worker never reviews their own work. The
        # domain model already makes it unconstructible; the constraint makes it
        # unstorable, so no path that bypasses the model can record it either.
        CheckConstraint(
            "reviewer_id IS NULL OR assigned_worker_id IS NULL "
            "OR reviewer_id <> assigned_worker_id",
            name="ck_tasks_reviewer_is_not_worker",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    feature_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("features.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    feature_plan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("feature_plans.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    plan_definition_key: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    capability: Mapped[str] = status_column()
    status: Mapped[str] = status_column()
    assigned_worker_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=True
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=True
    )
    active_revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    version: Mapped[int] = version_column()
    __mapper_args__ = {"version_id_col": version}


class TaskDependencyRow(Base):
    """One prerequisite edge between two Tasks."""

    __tablename__ = "task_dependencies"

    task_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    depends_on_task_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class TaskRevisionRow(RowMetadataMixin, Base):
    """One immutable Revision of a Task — append-only, never rewritten."""

    __tablename__ = "task_revisions"
    __table_args__ = (
        CheckConstraint("revision_number >= 1", name="ck_task_revisions_revision_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    task_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_worker_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    work_package_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    review_decision_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    qa_report_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
