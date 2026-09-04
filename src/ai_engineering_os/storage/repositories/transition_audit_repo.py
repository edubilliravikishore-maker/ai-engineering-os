"""Transition audit repository — append-only (ADR-005 5.8, ADR-006 6.3).

**There is no update method and no delete method.** This ledger exists so a
refused transition leaves a record the requesting actor cannot erase and the
OS cannot lose; a rewritable one would serve neither purpose.

Blueprint 7.2 writes here only on the failure path. ADR-006 6.3 amends that:
**every evaluated attempt is recorded**, carrying its outcome, so the history of
an entity is answerable from typed columns rather than by parsing the
unconstrained event payloads ADR-006 6.5 declined to fix.
"""

from uuid import UUID

from ai_engineering_os.domain.event import TransitionAuditRecord, TransitionOutcome
from ai_engineering_os.domain.identifiers import TransitionAuditId
from ai_engineering_os.storage.mappers.event import (
    to_domain_transition_audit,
    to_transition_audit_row,
)
from ai_engineering_os.storage.models.event import StateTransitionAuditRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["TransitionAuditRepository"]


class TransitionAuditRepository(BaseRepository[StateTransitionAuditRow]):
    """Appends and reads the immutable record of evaluated transitions."""

    row_type = StateTransitionAuditRow
    entity_name = "TransitionAuditRecord"

    async def add(self, record: TransitionAuditRecord) -> TransitionAuditRecord:
        """Appends ``record`` within the caller's transaction and returns it recorded."""
        row = to_transition_audit_row(record)
        self._stage(row)
        await self._flush()
        return to_domain_transition_audit(row)

    async def get_by_id(self, audit_id: TransitionAuditId) -> TransitionAuditRecord:
        """Returns the audit record stored under ``audit_id``."""
        return to_domain_transition_audit(await self._require_row(audit_id))

    async def list_by_entity(self, entity_id: UUID) -> tuple[TransitionAuditRecord, ...]:
        """Returns every evaluated transition against ``entity_id``, in append order.

        This is the query ADR-006 6.3 exists to make answerable: the complete
        history of an entity, refusals and successes alike.
        """
        rows = await self._rows_where(
            StateTransitionAuditRow.entity_id == entity_id,
            order_by=StateTransitionAuditRow.sequence_number,
        )
        return tuple(to_domain_transition_audit(row) for row in rows)

    async def list_rejections_for(self, entity_id: UUID) -> tuple[TransitionAuditRecord, ...]:
        """Returns only the refused attempts against ``entity_id``, in append order."""
        rows = await self._rows_where(
            StateTransitionAuditRow.entity_id == entity_id,
            StateTransitionAuditRow.outcome == TransitionOutcome.REJECTED.value,
            order_by=StateTransitionAuditRow.sequence_number,
        )
        return tuple(to_domain_transition_audit(row) for row in rows)
