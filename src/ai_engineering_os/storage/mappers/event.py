"""Event and transition-audit <-> row mapping (ADR-006 6.1, 6.11).

``sequence_number`` is read back but never written. The column is
``GENERATED ALWAYS AS IDENTITY``, so the row builders below omit it entirely and
the database assigns it. Reading it is not a violation of ADR-005 5.9: that
prohibition covers ``row_created_at`` and ``row_updated_at``, which remain
unread here as everywhere else in this package.
"""

from ai_engineering_os.domain.event import OSEvent, TransitionAuditRecord
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.event import OSEventRow, StateTransitionAuditRow

__all__ = [
    "to_domain_event",
    "to_domain_transition_audit",
    "to_event_row",
    "to_transition_audit_row",
]


def to_domain_event(row: OSEventRow) -> OSEvent:
    """Rebuilds the immutable event recorded by ``row``."""
    return reconstruct(
        OSEvent,
        {
            "id": row.id,
            "sequence_number": row.sequence_number,
            "event_type": row.event_type,
            "aggregate_type": row.aggregate_type,
            "aggregate_id": row.aggregate_id,
            "actor_id": row.actor_id,
            "actor_role": row.actor_role,
            "payload": row.payload,
            "occurred_at": row.occurred_at,
        },
        entity_id=row.id,
    )


def to_event_row(event: OSEvent) -> OSEventRow:
    """Builds the append-only row recording ``event``.

    ``sequence_number`` is deliberately absent: the database assigns it.
    """
    return OSEventRow(
        id=event.id,
        event_type=event.event_type.value,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        actor_id=event.actor_id,
        actor_role=event.actor_role.value,
        payload=dict(event.payload),
        occurred_at=event.occurred_at,
    )


def to_domain_transition_audit(row: StateTransitionAuditRow) -> TransitionAuditRecord:
    """Rebuilds the immutable transition audit record recorded by ``row``."""
    return reconstruct(
        TransitionAuditRecord,
        {
            "id": row.id,
            "sequence_number": row.sequence_number,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "from_state": row.from_state,
            "attempted_state": row.attempted_state,
            "outcome": row.outcome,
            "requested_by": row.requested_by,
            "requested_by_role": row.requested_by_role,
            "reasons": tuple(row.reasons),
            "occurred_at": row.occurred_at,
        },
        entity_id=row.id,
    )


def to_transition_audit_row(record: TransitionAuditRecord) -> StateTransitionAuditRow:
    """Builds the append-only row recording ``record``."""
    return StateTransitionAuditRow(
        id=record.id,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        from_state=record.from_state,
        attempted_state=record.attempted_state,
        outcome=record.outcome.value,
        requested_by=record.requested_by,
        requested_by_role=record.requested_by_role.value,
        reasons=[dict(reason) for reason in record.reasons],
        occurred_at=record.occurred_at,
    )
