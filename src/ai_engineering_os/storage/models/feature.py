"""Feature table (Blueprint 4.1 #1).

Authoritative current state: ``status`` moves DRAFT -> ... -> ACCEPTED, so the
row is updated in place and carries an optimistic-lock version (ADR-005 5.6).

The four scope and requirement lists are stored as JSONB (ADR-005 5.2): ADR-003
3.11 records that **the OS performs no text matching** against ``in_scope`` or
``out_of_scope``, so nothing ever queries inside them.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import FeatureStatus
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import (
    RowMetadataMixin,
    status_check,
    status_column,
    version_column,
)

__all__ = ["FeatureRow"]


class FeatureRow(RowMetadataMixin, Base):
    """A user or business capability requested by the Builder."""

    __tablename__ = "features"
    __table_args__ = (
        status_check("status", FeatureStatus, name="ck_features_status"),
        CheckConstraint("updated_at >= created_at", name="ck_features_timestamp_order"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    goal: Mapped[str] = mapped_column(String, nullable=False)
    coordinator_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = status_column()

    requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    in_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    out_of_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    acceptance_criteria: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    version: Mapped[int] = version_column()
    __mapper_args__ = {"version_id_col": version}
