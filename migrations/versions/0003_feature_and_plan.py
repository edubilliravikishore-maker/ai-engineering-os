"""Feature and Feature Plan

Features, Feature Plans, and plan-local task definitions.

`plan_task_definitions` is a child table because a Task records the plan-local
key it came from and the OS resolves that reference (ADR-005 5.2). `depends_on`
stays JSONB: plan acyclicity is a construction-time domain invariant
(ADR-004 4.11), so nothing queries inside it.

`features.slug` carries a UNIQUE constraint, recorded as a deliberate ruling in
ADR-005 5.14 because no domain validator states it.

Revision ID: 0003_feature_and_plan
Revises: 0002_actor_identity
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_feature_and_plan"
down_revision: str | None = "0002_actor_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "features",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("goal", sa.String(), nullable=False),
        sa.Column("coordinator_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("in_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("out_of_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("acceptance_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "status IN ('DRAFT', 'PLANNED', 'IN_PROGRESS', 'IN_VALIDATION', 'ACCEPTED')",
            name="ck_features_status",
        ),
        sa.CheckConstraint("updated_at >= created_at", name="ck_features_timestamp_order"),
        sa.ForeignKeyConstraint(["coordinator_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_features_coordinator_id"), "features", ["coordinator_id"], unique=False
    )
    op.create_table(
        "feature_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feature_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("required_capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
            "status IN ('DRAFT', 'READY', 'ACTIVE', 'COMPLETED', 'SUPERSEDED')",
            name="ck_feature_plans_status",
        ),
        sa.CheckConstraint("revision_number >= 1", name="ck_feature_plans_revision_number"),
        sa.ForeignKeyConstraint(["created_by"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feature_plans_feature_id"), "feature_plans", ["feature_id"], unique=False
    )
    op.create_table(
        "plan_task_definitions",
        sa.Column("feature_plan_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("depends_on", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "capability IN ('BACKEND', 'FRONTEND', 'QA')",
            name="ck_plan_task_definitions_capability",
        ),
        sa.ForeignKeyConstraint(["feature_plan_id"], ["feature_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("feature_plan_id", "key"),
    )
    op.create_index(
        op.f("ix_plan_task_definitions_feature_plan_id"),
        "plan_task_definitions",
        ["feature_plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_plan_task_definitions_feature_plan_id"), table_name="plan_task_definitions"
    )
    op.drop_table("plan_task_definitions")
    op.drop_index(op.f("ix_feature_plans_feature_id"), table_name="feature_plans")
    op.drop_table("feature_plans")
    op.drop_index(op.f("ix_features_coordinator_id"), table_name="features")
    op.drop_table("features")
