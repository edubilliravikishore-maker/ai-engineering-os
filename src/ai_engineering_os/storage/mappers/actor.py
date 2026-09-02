"""Actor <-> row mapping (ADR-005 5.1)."""

from ai_engineering_os.domain.actor import Actor
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.actor import ActorRow

__all__ = ["apply_actor", "to_actor_row", "to_domain_actor"]


def to_domain_actor(row: ActorRow) -> Actor:
    """Rebuilds the domain Actor recorded by ``row``."""
    return reconstruct(
        Actor,
        {
            "id": row.id,
            "role": row.role,
            "name": row.name,
            "domain": row.domain,
            "is_active": row.is_active,
            "capabilities": row.capabilities,
        },
        entity_id=row.id,
    )


def apply_actor(actor: Actor, row: ActorRow) -> None:
    """Writes ``actor`` onto ``row``. Persistence metadata is never touched."""
    row.role = actor.role.value
    row.name = actor.name
    row.domain = actor.domain
    row.is_active = actor.is_active
    row.capabilities = sorted(capability.value for capability in actor.capabilities)


def to_actor_row(actor: Actor) -> ActorRow:
    """Builds a new row for ``actor``, starting at optimistic-lock version 1."""
    row = ActorRow(id=actor.id, version=1)
    apply_actor(actor, row)
    return row
