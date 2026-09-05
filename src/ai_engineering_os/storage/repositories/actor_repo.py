"""Actor repository (ADR-005 5.1, 5.4).

Authoritative current state: ``is_active`` may change, so the row is updated
under optimistic locking.

This repository stores **identity only**. It is not a Domain Registry and offers
no domain-to-Coordinator mapping: ADR-003 3.10 defers that until the Coordinator
lifecycle is resolved.
"""

from ai_engineering_os.domain.actor import Actor
from ai_engineering_os.domain.enums import ActorRole
from ai_engineering_os.domain.identifiers import ActorId
from ai_engineering_os.storage.mappers.actor import apply_actor, to_actor_row, to_domain_actor
from ai_engineering_os.storage.models.actor import ActorRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["ActorRepository"]


class ActorRepository(BaseRepository[ActorRow]):
    """Reads and writes Actor identities."""

    row_type = ActorRow
    entity_name = "Actor"

    async def add(self, actor: Actor) -> None:
        """Records a new Actor within the caller's transaction."""
        self._stage(to_actor_row(actor))
        await self._flush()

    async def get_by_id(self, actor_id: ActorId) -> Actor:
        """Returns the Actor recorded under ``actor_id``.

        Raises:
            NotFoundError: if no such Actor is recorded.
        """
        return to_domain_actor(await self._require_row(actor_id))

    async def list_active_by_role(self, role: ActorRole) -> tuple[Actor, ...]:
        """Returns every active Actor holding ``role``, ordered by identifier.

        The order is the routing tie-break of ADR-007 7.3 and is applied here so
        it is a property of the query rather than of whichever caller happens to
        sort. It is **deterministic, not fair**: with several eligible Reviewers
        the lowest identifier receives everything. That is harmless while the
        eligible set has one member and is recorded as owed the moment it does
        not.

        Ordering by ``id`` is ordering by a stable application-generated value,
        not by a persistence-metadata timestamp, so ADR-005 5.9 is untouched.
        """
        rows = await self._rows_where(
            ActorRow.role == role.value,
            ActorRow.is_active.is_(True),
            order_by=ActorRow.id,
        )
        return tuple(to_domain_actor(row) for row in rows)

    async def save(self, actor: Actor) -> None:
        """Updates the recorded Actor under optimistic locking.

        Raises:
            NotFoundError: if no such Actor is recorded.
            ConcurrencyConflictError: if the record changed since it was read.
        """
        row = await self._require_row(actor.id)
        await self._save_row(row, lambda target: apply_actor(actor, target))
