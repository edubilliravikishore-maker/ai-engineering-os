"""Decision repository — append-only with additive acknowledgements (ADR-005 5.8).

**There is no update method for the Decision itself.** A recorded Decision is
permanent.

Acknowledgement is the one additive operation: it records that an actor received
and understood a Decision, never that they agreed with it (Design Session 008).
It is appended as a **child row**, which is precisely why acknowledgements are a
table rather than a JSONB array — appending to an array would require rewriting
an already-recorded ``decisions`` row (ADR-005 5.2, 5.8).
"""

from sqlalchemy import select

from ai_engineering_os.domain.decision import Decision
from ai_engineering_os.domain.enums import ActorRole
from ai_engineering_os.domain.identifiers import ActorId, DecisionId
from ai_engineering_os.storage.mappers.decision import (
    to_acknowledgement_rows,
    to_decision_row,
    to_domain_decision,
)
from ai_engineering_os.storage.models.decision import DecisionAcknowledgementRow, DecisionRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["DecisionRepository"]


class DecisionRepository(BaseRepository[DecisionRow]):
    """Appends and reads permanent Decisions and their acknowledgements."""

    row_type = DecisionRow
    entity_name = "Decision"

    async def add(self, decision: Decision) -> None:
        """Appends a Decision and any acknowledgements it already carries."""
        self._stage(to_decision_row(decision))
        await self._flush()
        for acknowledgement in to_acknowledgement_rows(decision):
            self._session.add(acknowledgement)
        await self._flush()

    async def get_by_id(self, decision_id: DecisionId) -> Decision:
        """Returns the Decision recorded under ``decision_id``, with acknowledgements."""
        row = await self._require_row(decision_id)
        return to_domain_decision(row, await self._acknowledgements_of(decision_id))

    async def add_acknowledgement(
        self, decision_id: DecisionId, *, actor_id: ActorId, actor_role: ActorRole
    ) -> Decision:
        """Appends one acknowledgement and returns the updated Decision.

        The domain performs the append: :meth:`Decision.acknowledge` rejects a
        duplicate acknowledgement by the same actor. The recorded ``decisions``
        row is never rewritten — only a child row is inserted.

        Raises:
            NotFoundError: if no such Decision is recorded.
            InvariantViolationError: if that actor already acknowledged it.
        """
        decision = await self.get_by_id(decision_id)
        updated = decision.acknowledge(actor_id=actor_id, actor_role=actor_role)
        appended = updated.acknowledgements[-1]
        self._session.add(
            DecisionAcknowledgementRow(
                decision_id=decision.id,
                actor_id=appended.actor_id,
                position=len(updated.acknowledgements) - 1,
                actor_role=appended.actor_role.value,
                acknowledged_at=appended.acknowledged_at,
            )
        )
        await self._flush()
        return updated

    async def _acknowledgements_of(
        self, decision_id: DecisionId
    ) -> list[DecisionAcknowledgementRow]:
        """Returns the acknowledgement rows of ``decision_id``, in recorded order."""
        statement = (
            select(DecisionAcknowledgementRow)
            .where(DecisionAcknowledgementRow.decision_id == decision_id)
            .order_by(DecisionAcknowledgementRow.position)
        )
        with self._translating():
            result = await self._session.execute(statement)
        return list(result.scalars().all())
