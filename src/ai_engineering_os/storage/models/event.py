"""Event store and transition audit tables (Blueprint 6, 7.2; ADR-006).

Both tables are append-only history (ADR-005 5.8), so neither carries an
optimistic-lock version column: a row that is never updated cannot lose an
update race (ADR-005 5.6).

Both carry ``sequence_number``, declared ``GENERATED ALWAYS AS IDENTITY``. It is
the **sole authority on append order** (ADR-006 6.1), and ``ALWAYS`` rather than
``BY DEFAULT`` so the application cannot supply it and the ordering authority
cannot be overridden from code. Gaps are expected and meaningless — a
rolled-back transaction consumes a value — so consumers compare, never count.

The ordering column exists so that the persistence metadata timestamps of
``RowMetadataMixin`` are **not** pressed into ordering service, which ADR-005 5.9
and ADR-004 4.15 forbid.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ai_engineering_os.domain.enums import ActorRole, SystemActor
from ai_engineering_os.domain.event import EventType, TransitionOutcome
from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.base import RowMetadataMixin, status_check, status_column

__all__ = ["INITIATOR_VALUES", "OSEventRow", "StateTransitionAuditRow", "initiator_check"]

INITIATOR_VALUES: tuple[str, ...] = tuple(member.value for member in ActorRole) + tuple(
    member.value for member in SystemActor
)
"""The seven values an initiator column admits: six Actor roles plus ``OS``.

Built from both enumerations rather than hand-listed, so the constraint cannot
drift from the ``Initiator = ActorRole | SystemActor`` alias the domain owns.
"""


def initiator_check(column: str, *, name: str) -> CheckConstraint:
    """Returns a ``CHECK`` admitting exactly the seven initiator values.

    ``status_check`` takes a single enumeration; an initiator spans two, because
    ADR-003 deliberately keeps ``SystemActor.OS`` out of ``ActorRole`` — the OS
    is infrastructure, not an agent.
    """
    admitted = ", ".join(f"'{value}'" for value in INITIATOR_VALUES)
    return CheckConstraint(f"{column} IN ({admitted})", name=name)


def actorless_only_for_os(role_column: str, id_column: str, *, name: str) -> CheckConstraint:
    """Returns a ``CHECK`` binding the absent Actor id to the OS and to nothing else.

    Written as an equivalence rather than an implication so it fails in both
    directions (ADR-006 6.8): a role other than ``OS`` may not omit its Actor id,
    and ``OS`` may not carry one, because the OS has no row in ``actors``.
    """
    return CheckConstraint(f"({role_column} = 'OS') = ({id_column} IS NULL)", name=name)


def _sequence_column() -> Mapped[int]:
    """Returns the append-order column (ADR-006 6.1)."""
    return mapped_column(BigInteger, Identity(always=True), nullable=False, unique=True)


class OSEventRow(RowMetadataMixin, Base):
    """One line in the append-only general event stream (Blueprint 6)."""

    __tablename__ = "os_events"
    __table_args__ = (
        status_check("event_type", EventType, name="ck_os_events_event_type"),
        initiator_check("actor_role", name="ck_os_events_actor_role"),
        actorless_only_for_os("actor_role", "actor_id", name="ck_os_events_actorless_only_for_os"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    sequence_number: Mapped[int] = _sequence_column()
    event_type: Mapped[str] = status_column()
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    actor_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    actor_role: Mapped[str] = status_column()
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StateTransitionAuditRow(RowMetadataMixin, Base):
    """One evaluated transition attempt, allowed or refused (ADR-006 6.3).

    ``aggregate_id`` has no foreign key here, and neither does ``entity_id``: a
    transition may be attempted against any lifecycle entity, and a single
    typed reference cannot span four of them without a discriminated key the
    architecture has not designed. ``entity_type`` carries the discriminator.
    """

    __tablename__ = "state_transitions_audit"
    __table_args__ = (
        status_check("outcome", TransitionOutcome, name="ck_transitions_audit_outcome"),
        initiator_check("requested_by_role", name="ck_transitions_audit_requested_by_role"),
        actorless_only_for_os(
            "requested_by_role", "requested_by", name="ck_transitions_audit_actorless_only_for_os"
        ),
        CheckConstraint(
            "(outcome = 'REJECTED') = (jsonb_array_length(reasons) > 0)",
            name="ck_transitions_audit_refusal_records_why",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    sequence_number: Mapped[int] = _sequence_column()
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    from_state: Mapped[str] = status_column()
    attempted_state: Mapped[str] = status_column()
    outcome: Mapped[str] = status_column()
    requested_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("actors.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    requested_by_role: Mapped[str] = status_column()
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
