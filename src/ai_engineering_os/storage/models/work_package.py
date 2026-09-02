"""Work Package table (Blueprint 4.1 #5, ADR-003 3.5, ADR-005 5.8).

**Hybrid, not append-only.** ADR-005 5.8 amends Blueprint 7.1's placement of this
table under append-only history, because it contradicted the five-value OS
projection ADR-003 3.5 requires:

* a ``DRAFT`` Work Package remains editable;
* ``SUBMITTED`` is persisted as the durable record;
* **submitted content becomes immutable** — enforced by the repository, which
  rejects a content change once the stored row has left ``DRAFT``;
* the **already-approved lifecycle transitions remain the sole authority** for
  status changes. Nothing here creates a second authority model.

``claims``, ``verification_guide`` and ``worker_notes`` stay JSONB (ADR-005 5.2):
ADR-003 3.7 records that ``claim_type`` is descriptive and **never feeds a
deterministic OS rule**, and ``CLAIMS_DEFINED`` needs only non-emptiness.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import WorkPackageStatus
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import (
    RowMetadataMixin,
    status_check,
    status_column,
    version_column,
)

__all__ = ["WORK_PACKAGE_CONTENT_COLUMNS", "WorkPackageRow"]

WORK_PACKAGE_CONTENT_COLUMNS: tuple[str, ...] = (
    "task_revision_id",
    "summary",
    "claims",
    "verification_guide",
    "worker_notes",
    "risks",
    "submitted_at",
)
"""Recorded content of a Work Package — everything except its projected status.

Named here rather than inferred so the immutability guarantee of ADR-005 5.8 is
a declared list a test can pin, not a rule spread across the repository.
"""


class WorkPackageRow(RowMetadataMixin, Base):
    """The Worker's structured handover object for one Task Revision."""

    __tablename__ = "work_packages"
    __table_args__ = (status_check("status", WorkPackageStatus, name="ck_work_packages_status"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    task_revision_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("task_revisions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = status_column()
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    verification_guide: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    worker_notes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risks: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    version: Mapped[int] = version_column()
    __mapper_args__ = {"version_id_col": version}
