"""Feature Plan and planned Task definition tables (Blueprint 4.1 #2).

``plan_task_definitions`` is a **child table** (ADR-005 5.2): a Task records the
plan-local ``plan_definition_key`` it came from, so the OS resolves that
reference, and ``PLAN_HAS_TASK_DEFINITIONS`` counts them.

``depends_on`` stays JSONB on the child row. Plan key uniqueness, dependency
resolvability, and acyclicity are validated at construction and classified
``SATISFIED_BY_DOMAIN_INVARIANT`` (ADR-004 4.11), so nothing queries inside it.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import CapabilityType, PlanStatus
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import (
    RowMetadataMixin,
    status_check,
    status_column,
    version_column,
)

__all__ = ["FeaturePlanRow", "PlanTaskDefinitionRow"]


class FeaturePlanRow(RowMetadataMixin, Base):
    """The Coordinator's plan for delivering a Feature."""

    __tablename__ = "feature_plans"
    __table_args__ = (
        status_check("status", PlanStatus, name="ck_feature_plans_status"),
        CheckConstraint("revision_number >= 1", name="ck_feature_plans_revision_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    feature_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("features.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = status_column()
    required_capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    version: Mapped[int] = version_column()
    __mapper_args__ = {"version_id_col": version}


class PlanTaskDefinitionRow(RowMetadataMixin, Base):
    """A planned Task inside a Feature Plan, keyed plan-locally (ADR-003 3.8)."""

    __tablename__ = "plan_task_definitions"
    __table_args__ = (
        status_check("capability", CapabilityType, name="ck_plan_task_definitions_capability"),
    )

    feature_plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("feature_plans.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    capability: Mapped[str] = status_column()
    depends_on: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
