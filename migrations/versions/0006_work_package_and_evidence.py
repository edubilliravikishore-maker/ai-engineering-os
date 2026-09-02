"""Work Packages and Evidence

The hybrid Work Package record and append-only Evidence.

`work_packages` carries a version column: it is NOT append-only (ADR-005 5.8).
DRAFT content is editable, SUBMITTED is the durable record, submitted content is
frozen by the repository, and the approved lifecycle transitions remain the sole
authority for status.

Evidence content is stored inline; `checksum` is the authoritative integrity
record (Blueprint 4.1 #6, 14 item 2).

Revision ID: 0006_work_package_and_evidence
Revises: 0005_qa_and_review
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_work_package_and_evidence"
down_revision: str | None = "0005_qa_and_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_revision_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("claims", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_guide", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("worker_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risks", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('DRAFT', 'SUBMITTED', 'VALIDATED', 'REVIEWED', 'ACCEPTED', 'REJECTED')",
            name="ck_work_packages_status",
        ),
        sa.ForeignKeyConstraint(["task_revision_id"], ["task_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_work_packages_task_revision_id"),
        "work_packages",
        ["task_revision_id"],
        unique=True,
    )
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("work_package_id", sa.Uuid(), nullable=True),
        sa.Column("qa_report_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verified_by_os", sa.Boolean(), nullable=False),
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
            "NOT (source_type = 'WORKER' AND verified_by_os)",
            name="ck_evidence_records_worker_never_os_verified",
        ),
        sa.CheckConstraint(
            "checksum ~ '^[0-9a-f]{64}$'", name="ck_evidence_records_checksum_format"
        ),
        sa.CheckConstraint(
            "evidence_type IN ('GIT_DIFF', 'TEST_OUTPUT', 'API_RESPONSE', 'BUILD_LOG', 'DB_VERIFICATION', 'REASONING')",
            name="ck_evidence_records_evidence_type",
        ),
        sa.CheckConstraint(
            "source_type IN ('SYSTEM', 'WORKER')", name="ck_evidence_records_source_type"
        ),
        sa.CheckConstraint(
            "work_package_id IS NOT NULL OR qa_report_id IS NOT NULL",
            name="ck_evidence_records_attachment",
        ),
        sa.ForeignKeyConstraint(["qa_report_id"], ["qa_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_package_id"], ["work_packages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_records_qa_report_id"), "evidence_records", ["qa_report_id"], unique=False
    )
    op.create_index(
        op.f("ix_evidence_records_work_package_id"),
        "evidence_records",
        ["work_package_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_evidence_records_qa_report_id"), table_name="evidence_records")
    op.drop_index(op.f("ix_evidence_records_work_package_id"), table_name="evidence_records")
    op.drop_table("evidence_records")
    op.drop_index(op.f("ix_work_packages_task_revision_id"), table_name="work_packages")
    op.drop_table("work_packages")
