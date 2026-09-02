"""Task, dependencies, and Revisions

Tasks, their prerequisite edges, and their append-only Revision history.

`tasks.feature_plan_id` and `plan_definition_key` are both NOT NULL (ADR-003
3.12, ADR-004 4.8): without them the originating plan cannot be evaluated.

`task_revisions` carries NO status column and NO version column (ADR-003 3.1).
A Revision is never rewritten or re-marked; the authoritative active-revision
pointer is `tasks.active_revision_number`.

Revision ID: 0004_task_and_revisions
Revises: 0003_feature_and_plan
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_task_and_revisions"
down_revision: str | None = "0003_feature_and_plan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feature_id", sa.Uuid(), nullable=False),
        sa.Column("feature_plan_id", sa.Uuid(), nullable=False),
        sa.Column("plan_definition_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("assigned_worker_id", sa.Uuid(), nullable=True),
        sa.Column("active_revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "row_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "row_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "capability IN ('BACKEND', 'FRONTEND', 'QA')", name="ck_tasks_capability"
        ),
        sa.CheckConstraint(
            "status IN ('CREATED', 'PENDING_DEPENDENCIES', 'READY', 'ASSIGNED', 'IN_PROGRESS', 'SUBMITTED', 'IN_REVIEW', 'IN_QA', 'REVISION_REQUIRED', 'ACCEPTED')",
            name="ck_tasks_status",
        ),
        sa.CheckConstraint("active_revision_number >= 0", name="ck_tasks_active_revision_number"),
        sa.CheckConstraint("updated_at >= created_at", name="ck_tasks_timestamp_order"),
        sa.ForeignKeyConstraint(["assigned_worker_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["feature_plan_id"], ["feature_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_feature_id"), "tasks", ["feature_id"], unique=False)
    op.create_index(op.f("ix_tasks_feature_plan_id"), "tasks", ["feature_plan_id"], unique=False)
    op.create_table(
        "task_dependencies",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("depends_on_task_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("task_id", "depends_on_task_id"),
    )
    op.create_index(
        op.f("ix_task_dependencies_task_id"), "task_dependencies", ["task_id"], unique=False
    )
    op.create_table(
        "task_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_by_worker_id", sa.Uuid(), nullable=False),
        sa.Column("work_package_id", sa.Uuid(), nullable=True),
        sa.Column("review_decision_id", sa.Uuid(), nullable=True),
        sa.Column("qa_report_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "row_created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "row_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("revision_number >= 1", name="ck_task_revisions_revision_number"),
        sa.ForeignKeyConstraint(["created_by_worker_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_revisions_task_id"), "task_revisions", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_task_revisions_task_id"), table_name="task_revisions")
    op.drop_table("task_revisions")
    op.drop_index(op.f("ix_task_dependencies_task_id"), table_name="task_dependencies")
    op.drop_table("task_dependencies")
    op.drop_index(op.f("ix_tasks_feature_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_feature_plan_id"), table_name="tasks")
    op.drop_table("tasks")
