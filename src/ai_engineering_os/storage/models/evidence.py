"""Evidence record table (Blueprint 4.1 #6, Design Session 005).

Append-only history. Evidence proves the Claims inside a Work Package, or the
results inside a QA Report, and is never rewritten once recorded.

Content is stored **inline** (Blueprint 14, item 2). The threshold at which a
payload would instead be stored as a durable URI reference is an implementation
and configuration parameter that Checkpoint 4 does not decide; ``checksum``
remains the authoritative integrity record either way.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import EvidenceSourceType, EvidenceType
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import RowMetadataMixin, status_check, status_column

__all__ = ["EvidenceRecordRow"]


class EvidenceRecordRow(RowMetadataMixin, Base):
    """A durable, integrity-verifiable record supporting a Claim or QA result."""

    __tablename__ = "evidence_records"
    __table_args__ = (
        status_check("source_type", EvidenceSourceType, name="ck_evidence_records_source_type"),
        status_check("evidence_type", EvidenceType, name="ck_evidence_records_evidence_type"),
        CheckConstraint(
            "work_package_id IS NOT NULL OR qa_report_id IS NOT NULL",
            name="ck_evidence_records_attachment",
        ),
        CheckConstraint(
            "NOT (source_type = 'WORKER' AND verified_by_os)",
            name="ck_evidence_records_worker_never_os_verified",
        ),
        CheckConstraint(
            "checksum ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_records_checksum_format",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    source_type: Mapped[str] = status_column()
    evidence_type: Mapped[str] = status_column()
    content: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    work_package_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("work_packages.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    qa_report_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("qa_reports.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    verified_by_os: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
