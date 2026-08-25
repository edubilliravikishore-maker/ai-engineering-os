"""Decisions, acknowledgements, and reviewer decisions (Blueprint 4.1 #8, DS-004/008).

Decisions are recorded permanently. Acknowledgement is additive: it records that
an actor received and understood a decision, never that they agreed with it.
"""

from datetime import datetime

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, utc_now
from ai_engineering_os.domain.enums import ActorRole, DecisionScope, ReviewOutcome
from ai_engineering_os.domain.errors import InvariantViolationError
from ai_engineering_os.domain.identifiers import (
    ActorId,
    DecisionId,
    ReviewDecisionId,
    TaskRevisionId,
)

__all__ = [
    "DECISION_AUTHORITY",
    "Decision",
    "DecisionAcknowledgement",
    "ReviewDecision",
]

DECISION_AUTHORITY: dict[DecisionScope, frozenset[ActorRole]] = {
    DecisionScope.FEATURE: frozenset(
        {ActorRole.COORDINATOR, ActorRole.ORCHESTRATOR, ActorRole.BUILDER}
    ),
    DecisionScope.SYSTEM: frozenset({ActorRole.ORCHESTRATOR, ActorRole.BUILDER}),
    DecisionScope.BUSINESS: frozenset({ActorRole.BUILDER}),
}
"""Who may record a Decision at each scope.

Design Session 004 establishes the authority chain Worker -> Coordinator ->
Orchestrator -> Builder, so a higher authority may also decide a narrower scope.
A Worker never holds decision authority at any scope.
"""


class DecisionAcknowledgement(DomainModel):
    """A record that an actor received and understood a Decision (DS-008)."""

    actor_id: ActorId
    actor_role: ActorRole
    acknowledged_at: datetime = Field(default_factory=utc_now)


class Decision(DomainModel):
    """An authoritative decision recorded by AI Engineering OS."""

    id: DecisionId
    scope: DecisionScope
    decided_by_role: ActorRole
    decided_by_id: ActorId
    problem: NonEmptyText
    decision_text: NonEmptyText
    reasoning: NonEmptyText
    alternatives_considered: tuple[NonEmptyText, ...] = ()
    affected_domains: tuple[NonEmptyText, ...] = ()
    acknowledgements: tuple[DecisionAcknowledgement, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _decider_must_hold_authority(self) -> "Decision":
        permitted = DECISION_AUTHORITY[self.scope]
        if self.decided_by_role not in permitted:
            raise ValueError(
                f"{self.decided_by_role} cannot record a {self.scope} scoped Decision; "
                f"permitted roles are {sorted(permitted)}"
            )
        return self

    @model_validator(mode="after")
    def _acknowledgements_must_be_unique(self) -> "Decision":
        actors = [ack.actor_id for ack in self.acknowledgements]
        if len(set(actors)) != len(actors):
            raise ValueError("A Decision cannot record duplicate acknowledgements per actor")
        return self

    def is_acknowledged_by(self, actor_id: ActorId) -> bool:
        """Returns whether ``actor_id`` has acknowledged this Decision."""
        return any(ack.actor_id == actor_id for ack in self.acknowledgements)

    def acknowledge(
        self,
        *,
        actor_id: ActorId,
        actor_role: ActorRole,
        acknowledged_at: datetime | None = None,
    ) -> "Decision":
        """Returns a new Decision with the acknowledgement appended.

        Raises:
            InvariantViolationError: if the actor already acknowledged this Decision.
        """
        if self.is_acknowledged_by(actor_id):
            raise InvariantViolationError("This actor has already acknowledged the Decision")
        acknowledgement = DecisionAcknowledgement(
            actor_id=actor_id,
            actor_role=actor_role,
            acknowledged_at=acknowledged_at or utc_now(),
        )
        return self._evolve(acknowledgements=(*self.acknowledgements, acknowledgement))


class ReviewDecision(DomainModel):
    """A Reviewer's outcome for one Task Revision.

    Blueprint 5.2 requires review notes for an approval and explicit feedback
    for a change request, so notes are mandatory in both cases.
    """

    id: ReviewDecisionId
    task_revision_id: TaskRevisionId
    reviewer_id: ActorId
    outcome: ReviewOutcome
    notes: NonEmptyText
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def is_approved(self) -> bool:
        """Returns whether the Reviewer approved the Revision."""
        return self.outcome is ReviewOutcome.APPROVED
