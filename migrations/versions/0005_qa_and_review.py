"""QA Reports, defects, and Review Decisions

Append-only QA audit history and Reviewer outcomes.

Nothing here identifies a current or latest QA Report: no sequence number, no
`current_report_id`, no marker of any kind. The authoritative QA-result
selection mechanism remains UNRESOLVED (ADR-004 4.15, Blueprint 14 item 18).

`qa_defects` scope columns carry referential foreign keys, so a nonexistent
identifier is unstorable (ADR-005 5.14). Both stay nullable and both-null
remains valid: unresolved scope must stay representable (ADR-004 4.8).

Ordered before work packages because `evidence_records` references
`qa_reports`.

Revision ID: 0005_qa_and_review
Revises: 0004_task_and_revisions
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_qa_and_review"
down_revision: str | None = "0004_task_and_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "qa_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feature_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("task_revision_id", sa.Uuid(), nullable=True),
        sa.Column("is_final_pass", sa.Boolean(), nullable=False),
        sa.Column("tested_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            "status IN ('PASSED', 'FAILED', 'BLOCKED')", name="ck_qa_reports_status"
        ),
        sa.ForeignKeyConstraint(["feature_id"], ["features.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_revision_id"], ["task_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_qa_reports_feature_id"), "qa_reports", ["feature_id"], unique=False)
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_revision_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.String(), nullable=False),
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
            "outcome IN ('APPROVED', 'CHANGES_REQUESTED')", name="ck_review_decisions_outcome"
        ),
        sa.ForeignKeyConstraint(["reviewer_id"], ["actors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_revision_id"], ["task_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_decisions_task_revision_id"),
        "review_decisions",
        ["task_revision_id"],
        unique=False,
    )
    op.create_table(
        "qa_defects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("qa_report_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("severity", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.String(length=255), nullable=False),
        sa.Column("is_blocker", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("scope_task_id", sa.Uuid(), nullable=True),
        sa.Column("scope_feature_id", sa.Uuid(), nullable=True),
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
        sa.CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="ck_qa_defects_status"),
        sa.CheckConstraint(
            "NOT (scope_task_id IS NOT NULL AND scope_feature_id IS NOT NULL)",
            name="ck_qa_defects_singular_scope_association",
        ),
        sa.ForeignKeyConstraint(["qa_report_id"], ["qa_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scope_feature_id"], ["features.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scope_task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_qa_defects_qa_report_id"), "qa_defects", ["qa_report_id"], unique=False
    )
    op.create_index(
        op.f("ix_qa_defects_scope_task_id"), "qa_defects", ["scope_task_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_qa_defects_qa_report_id"), table_name="qa_defects")
    op.drop_index(op.f("ix_qa_defects_scope_task_id"), table_name="qa_defects")
    op.drop_table("qa_defects")
    op.drop_index(op.f("ix_review_decisions_task_revision_id"), table_name="review_decisions")
    op.drop_table("review_decisions")
    op.drop_index(op.f("ix_qa_reports_feature_id"), table_name="qa_reports")
    op.drop_table("qa_reports")
