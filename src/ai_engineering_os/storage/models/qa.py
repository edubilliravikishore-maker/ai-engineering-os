"""QA Report and QA Defect tables (Blueprint 4.1 #7, Design Session 009).

Both are **append-only audit history** (ADR-004 4.15). Repeat QA is normal: a
report is scoped to a Task Revision, and the rework loop produces more of them.
**Nothing here limits a Feature to one QA Report.**

``qa_round`` records which build-and-check cycle of the Feature a report belongs
to (ADR-007 7.4), which is how the current defect position is selected. It is
**not** a recency marker: there is still no sequence number, no
``current_report_id``, no timestamp comparison and no "latest" flag. The round
is stamped by the Kernel from ``features.qa_round`` when the report is recorded,
and reports from earlier rounds stay exactly as they were written.

``qa_defects`` is a **child table** (ADR-005 5.2) because
``QAInScopeZeroDefectsRule`` resolves ``Defect -> Task -> Feature`` per defect.

``results`` and ``tested_scope`` stay JSONB: no rule inspects an individual test
result.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import DefectStatus, QAStatus
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import RowMetadataMixin, status_check, status_column

__all__ = ["QADefectRow", "QAReportRow"]


class QAReportRow(RowMetadataMixin, Base):
    """A structured, machine-first QA verification record."""

    __tablename__ = "qa_reports"
    __table_args__ = (
        status_check("status", QAStatus, name="ck_qa_reports_status"),
        CheckConstraint("qa_round >= 1", name="ck_qa_reports_qa_round"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    feature_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("features.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = status_column()
    task_revision_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("task_revisions.id", ondelete="RESTRICT"), nullable=True
    )
    qa_round: Mapped[int] = mapped_column(Integer, nullable=False)
    is_final_pass: Mapped[bool] = mapped_column(nullable=False)
    tested_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QADefectRow(RowMetadataMixin, Base):
    """A defect discovered by QA.

    **Scope is an association, never a declaration** (ADR-003 3.11). There is no
    ``in_scope`` boolean and none may be added. The two scope columns are both
    nullable and carry referential foreign keys, so a *nonexistent* identifier
    cannot be stored (ADR-005 5.14). Exactly one may be set, or **neither** —
    both-null is the valid "unresolved scope" state ADR-004 4.8 requires to stay
    representable.
    """

    __tablename__ = "qa_defects"
    __table_args__ = (
        status_check("status", DefectStatus, name="ck_qa_defects_status"),
        CheckConstraint(
            "NOT (scope_task_id IS NOT NULL AND scope_feature_id IS NOT NULL)",
            name="ck_qa_defects_singular_scope_association",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    qa_report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("qa_reports.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    severity: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(String(255), nullable=False)
    is_blocker: Mapped[bool] = mapped_column(nullable=False)
    status: Mapped[str] = status_column()
    scope_task_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    scope_feature_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("features.id", ondelete="RESTRICT"), nullable=True
    )
