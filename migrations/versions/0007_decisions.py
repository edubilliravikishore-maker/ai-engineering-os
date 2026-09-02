"""Decisions and acknowledgements

Permanent Decisions and their additive acknowledgements.

Acknowledgements are a child table rather than a JSONB array (ADR-005 5.2, 5.8):
appending one to an array would require rewriting an already-recorded
`decisions` row.

Revision ID: 0007_decisions
Revises: 0006_work_package_and_evidence
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_decisions"
down_revision: str | None = "0006_work_package_and_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("decided_by_role", sa.String(length=64), nullable=False),
        sa.Column("decided_by_id", sa.Uuid(), nullable=False),
        sa.Column("problem", sa.String(), nullable=False),
        sa.Column("decision_text", sa.String(), nullable=False),
        sa.Column("reasoning", sa.String(), nullable=False),
        sa.Column(
            "alternatives_considered", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("affected_domains", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.CheckConstraint(
            "decided_by_role IN ('BUILDER', 'ORCHESTRATOR', 'COORDINATOR', 'WORKER', 'REVIEWER', 'QA')",
            name="ck_decisions_decided_by_role",
        ),
        sa.CheckConstraint("scope IN ('FEATURE', 'SYSTEM', 'BUSINESS')", name="ck_decisions_scope"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "decision_acknowledgements",
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("actor_role", sa.String(length=64), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
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
            "actor_role IN ('BUILDER', 'ORCHESTRATOR', 'COORDINATOR', 'WORKER', 'REVIEWER', 'QA')",
            name="ck_decision_acknowledgements_actor_role",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("decision_id", "actor_id"),
    )
    op.create_index(
        op.f("ix_decision_acknowledgements_decision_id"),
        "decision_acknowledgements",
        ["decision_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_decision_acknowledgements_decision_id"), table_name="decision_acknowledgements"
    )
    op.drop_table("decision_acknowledgements")
    op.drop_table("decisions")
