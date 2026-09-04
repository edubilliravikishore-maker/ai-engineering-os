"""Domain events and the transition audit record (Blueprint 4.1, 6; ADR-006).

These types live in ``domain`` rather than in ``events`` by the ruling of
ADR-006 6.11. ``storage`` persists them and ``events`` announces them, and a
vocabulary two sibling layers both consume belongs to the layer beneath both —
the same resolution ADR-004 4.7 made for ``TransitionCondition``.

Two records are defined here, and they answer different questions:

* :class:`OSEvent` is the **general stream**. Every significant OS action
  appends one. Its ``payload`` is deliberately unconstrained (ADR-006 6.5).
* :class:`TransitionAuditRecord` is the **enforcement ledger**. Every evaluated
  transition appends one, whether it was allowed or refused (ADR-006 6.3), with
  the detail in typed fields rather than in a payload.

Neither is ever rewritten. Both are appended and read (ADR-005 5.8).
"""

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, utc_now
from ai_engineering_os.domain.enums import Initiator, SystemActor
from ai_engineering_os.domain.identifiers import ActorId, EventId, TransitionAuditId

__all__ = [
    "EventType",
    "OSEvent",
    "TransitionAuditRecord",
    "TransitionOutcome",
]


class EventType(StrEnum):
    """The thirteen Foundation v1 event types (Blueprint 6, ADR-006 6.4).

    The vocabulary is **closed**. A fourteenth entry is a migration, deliberately,
    so a misspelled type is rejected by the database rather than silently
    becoming an event kind no subscriber listens for.

    ``ESCALATION_RAISED`` is one of the thirteen and is recorded as a forward
    reference (Blueprint 6). **It creates no ``BLOCKED`` state**: D-1 remains
    deferred and no status constraint anywhere admits it (ADR-003 3.3).
    """

    FEATURE_CREATED = "FeatureCreated"
    FEATURE_PLAN_CREATED = "FeaturePlanCreated"
    FEATURE_PLAN_ACTIVATED = "FeaturePlanActivated"
    TASK_ASSIGNED = "TaskAssigned"
    TASK_STARTED = "TaskStarted"
    WORK_PACKAGE_SUBMITTED = "WorkPackageSubmitted"
    EVIDENCE_ATTACHED = "EvidenceAttached"
    STATE_TRANSITION_ALLOWED = "StateTransitionAllowed"
    STATE_TRANSITION_REJECTED = "StateTransitionRejected"
    REVIEW_COMPLETED = "ReviewCompleted"
    QA_REPORT_SUBMITTED = "QAReportSubmitted"
    FEATURE_ACCEPTED = "FeatureAccepted"
    ESCALATION_RAISED = "EscalationRaised"


class TransitionOutcome(StrEnum):
    """Whether an evaluated transition was permitted (ADR-006 6.3)."""

    ALLOWED = "ALLOWED"
    REJECTED = "REJECTED"


class _AppendOnlyRecord(DomainModel):
    """Shared shape of the two append-only records: ordering and attribution.

    ``sequence_number`` is the **sole authority on append order** (ADR-006 6.1).
    It is ``None`` before the record is appended and populated on read, because
    the column is ``GENERATED ALWAYS`` and the application cannot supply it.

    It is **not** persistence metadata in the ADR-005 5.9 sense. That prohibition
    covers ``row_created_at`` and ``row_updated_at``, which no mapper reads;
    ``sequence_number`` exists precisely so those timestamps are never pressed
    into ordering service, and it is the token a subscriber resumes from
    (ADR-006 6.6).
    """

    sequence_number: int | None = None

    @model_validator(mode="after")
    def _os_is_the_only_actorless_initiator(self) -> "_AppendOnlyRecord":
        """Only the OS may be recorded without an Actor id (ADR-006 6.8).

        ``SystemActor.OS`` is the sole permitted initiator of four Task
        transitions, so recording a person for them would be false. The OS is
        infrastructure and has no row in ``actors``, so its id is null — and
        the null is confined to exactly that case, here and by a database
        ``CHECK``.
        """
        role, actor_id = self._initiator
        if actor_id is None and role is not SystemActor.OS:
            raise ValueError(f"An Actor id is required when the initiator is {role}")
        if actor_id is not None and role is SystemActor.OS:
            raise ValueError("The OS is not an Actor and cannot carry an Actor id")
        return self

    @property
    def _initiator(self) -> tuple[Initiator, ActorId | None]:
        """Returns the initiator role and id this record attributes itself to."""
        raise NotImplementedError


class OSEvent(_AppendOnlyRecord):
    """One line in the append-only general stream (Blueprint 6).

    ``payload`` carries whatever the producing action recorded. **It has no
    per-event-type schema** (ADR-006 6.5): the Kernel and the API that will
    shape these payloads do not exist yet, and an append-only row cannot be
    reshaped once a guess proves wrong. The structured detail the OS enforces
    against lives in :class:`TransitionAuditRecord` instead.
    """

    id: EventId
    event_type: EventType
    aggregate_type: NonEmptyText
    aggregate_id: UUID
    actor_id: ActorId | None = None
    actor_role: Initiator
    payload: Mapping[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utc_now)

    @property
    def _initiator(self) -> tuple[Initiator, ActorId | None]:
        return self.actor_role, self.actor_id


class TransitionAuditRecord(_AppendOnlyRecord):
    """One evaluated transition attempt, allowed or refused (ADR-006 6.3).

    Blueprint 7.2 writes to this ledger only on the failure path. ADR-006 6.3
    amends that: every evaluated attempt is recorded, carrying ``outcome``, so
    "what happened to this Task?" is answerable from typed columns rather than
    by parsing the unconstrained payloads of :class:`OSEvent`.

    ``reasons`` holds the Rule Engine's structured rejection reasons. It is
    **empty on an allowed transition and non-empty on a rejected one** — a
    refusal without a recorded reason would leave the requesting actor unable
    to learn what to fix.
    """

    id: TransitionAuditId
    entity_type: NonEmptyText
    entity_id: UUID
    from_state: NonEmptyText
    attempted_state: NonEmptyText
    outcome: TransitionOutcome
    requested_by: ActorId | None = None
    requested_by_role: Initiator
    reasons: tuple[Mapping[str, Any], ...] = ()
    occurred_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _a_refusal_records_why(self) -> "TransitionAuditRecord":
        """A rejection carries reasons; an allowed transition carries none."""
        if self.outcome is TransitionOutcome.REJECTED and not self.reasons:
            raise ValueError("A rejected transition must record why it was refused")
        if self.outcome is TransitionOutcome.ALLOWED and self.reasons:
            raise ValueError("An allowed transition records no rejection reasons")
        return self

    @property
    def _initiator(self) -> tuple[Initiator, ActorId | None]:
        return self.requested_by_role, self.requested_by
