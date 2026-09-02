"""Decision, acknowledgement, and Review Decision <-> row mapping."""

from collections.abc import Sequence

from ai_engineering_os.domain.decision import Decision, DecisionAcknowledgement, ReviewDecision
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.decision import (
    DecisionAcknowledgementRow,
    DecisionRow,
    ReviewDecisionRow,
)

__all__ = [
    "to_acknowledgement_row",
    "to_acknowledgement_rows",
    "to_decision_row",
    "to_domain_decision",
    "to_domain_review_decision",
    "to_review_decision_row",
]


def to_domain_decision(
    row: DecisionRow, acknowledgements: Sequence[DecisionAcknowledgementRow]
) -> Decision:
    """Rebuilds the Decision recorded by ``row`` and its acknowledgement rows."""
    ordered = sorted(acknowledgements, key=lambda ack: ack.position)
    return reconstruct(
        Decision,
        {
            "id": row.id,
            "scope": row.scope,
            "decided_by_role": row.decided_by_role,
            "decided_by_id": row.decided_by_id,
            "problem": row.problem,
            "decision_text": row.decision_text,
            "reasoning": row.reasoning,
            "alternatives_considered": row.alternatives_considered,
            "affected_domains": row.affected_domains,
            "acknowledgements": [
                {
                    "actor_id": ack.actor_id,
                    "actor_role": ack.actor_role,
                    "acknowledged_at": ack.acknowledged_at,
                }
                for ack in ordered
            ],
            "created_at": row.created_at,
        },
        entity_id=row.id,
    )


def to_decision_row(decision: Decision) -> DecisionRow:
    """Builds the append-only row recording ``decision``."""
    return DecisionRow(
        id=decision.id,
        scope=decision.scope.value,
        decided_by_role=decision.decided_by_role.value,
        decided_by_id=decision.decided_by_id,
        problem=decision.problem,
        decision_text=decision.decision_text,
        reasoning=decision.reasoning,
        alternatives_considered=list(decision.alternatives_considered),
        affected_domains=list(decision.affected_domains),
        created_at=decision.created_at,
    )


def to_acknowledgement_row(
    decision: Decision, acknowledgement: DecisionAcknowledgement, position: int
) -> DecisionAcknowledgementRow:
    """Builds the child row recording one acknowledgement of ``decision``."""
    return DecisionAcknowledgementRow(
        decision_id=decision.id,
        actor_id=acknowledgement.actor_id,
        position=position,
        actor_role=acknowledgement.actor_role.value,
        acknowledged_at=acknowledgement.acknowledged_at,
    )


def to_acknowledgement_rows(decision: Decision) -> list[DecisionAcknowledgementRow]:
    """Builds the child rows recording ``decision``'s acknowledgements, in order."""
    return [
        to_acknowledgement_row(decision, acknowledgement, position)
        for position, acknowledgement in enumerate(decision.acknowledgements)
    ]


def to_domain_review_decision(row: ReviewDecisionRow) -> ReviewDecision:
    """Rebuilds the immutable Review Decision recorded by ``row``."""
    return reconstruct(
        ReviewDecision,
        {
            "id": row.id,
            "task_revision_id": row.task_revision_id,
            "reviewer_id": row.reviewer_id,
            "outcome": row.outcome,
            "notes": row.notes,
            "created_at": row.created_at,
        },
        entity_id=row.id,
    )


def to_review_decision_row(review: ReviewDecision) -> ReviewDecisionRow:
    """Builds the append-only row recording ``review``."""
    return ReviewDecisionRow(
        id=review.id,
        task_revision_id=review.task_revision_id,
        reviewer_id=review.reviewer_id,
        outcome=review.outcome.value,
        notes=review.notes,
        created_at=review.created_at,
    )
