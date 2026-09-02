"""Decision, acknowledgement, and Review Decision tables (Blueprint 4.1 #8, #8b).

All three are append-only history.

``decision_acknowledgements`` is a **child table** (ADR-005 5.2, 5.8) for a
specific reason: acknowledgement is additive, and appending one to a JSONB array
would require rewriting an already-recorded ``decisions`` row.

``ReviewDecision`` is a distinct table, deliberately not merged into
``decisions`` (ADR-003 3.2): merging would place every routine code review into
permanent architectural decision history, and ``REVIEWER`` holds authority at no
``DecisionScope``.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import ActorRole, DecisionScope, ReviewOutcome
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import RowMetadataMixin, status_check, status_column

__all__ = ["DecisionAcknowledgementRow", "DecisionRow", "ReviewDecisionRow"]


class DecisionRow(RowMetadataMixin, Base):
    """An authoritative architectural, system, or business decision."""

    __tablename__ = "decisions"
    __table_args__ = (
        status_check("scope", DecisionScope, name="ck_decisions_scope"),
        status_check("decided_by_role", ActorRole, name="ck_decisions_decided_by_role"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    scope: Mapped[str] = status_column()
    decided_by_role: Mapped[str] = status_column()
    decided_by_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    problem: Mapped[str] = mapped_column(String, nullable=False)
    decision_text: Mapped[str] = mapped_column(String, nullable=False)
    reasoning: Mapped[str] = mapped_column(String, nullable=False)
    alternatives_considered: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    affected_domains: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DecisionAcknowledgementRow(RowMetadataMixin, Base):
    """A record that an actor received and understood a Decision (DS-008)."""

    __tablename__ = "decision_acknowledgements"
    __table_args__ = (
        status_check("actor_role", ActorRole, name="ck_decision_acknowledgements_actor_role"),
    )

    decision_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("decisions.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    actor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_role: Mapped[str] = status_column()
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReviewDecisionRow(RowMetadataMixin, Base):
    """A Reviewer's outcome for one Task Revision. Notes are mandatory."""

    __tablename__ = "review_decisions"
    __table_args__ = (status_check("outcome", ReviewOutcome, name="ck_review_decisions_outcome"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    task_revision_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("task_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reviewer_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    outcome: Mapped[str] = status_column()
    notes: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
