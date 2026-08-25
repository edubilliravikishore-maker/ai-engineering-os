"""Actor identity for AI Engineering OS (Blueprint 4.1 #9).

Only the identity and authority attributes required by the domain rules are
modelled here. Agent runtimes, prompts, and provider integrations are outside
the domain layer entirely.
"""

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText
from ai_engineering_os.domain.enums import ActorRole, CapabilityType
from ai_engineering_os.domain.identifiers import ActorId

__all__ = ["Actor"]


class Actor(DomainModel):
    """A Builder, Orchestrator, Coordinator, Worker, Reviewer, or QA identity."""

    id: ActorId
    role: ActorRole
    name: NonEmptyText
    domain: NonEmptyText | None = None
    is_active: bool = True
    capabilities: frozenset[CapabilityType] = Field(default_factory=frozenset)

    @model_validator(mode="after")
    def _worker_must_declare_capability(self) -> "Actor":
        """A Worker is selected by capability, so it must declare at least one.

        Required by Blueprint 5.2 ``READY -> ASSIGNED``: "Worker ID is active
        and possesses matching capability."
        """
        if self.role is ActorRole.WORKER and not self.capabilities:
            raise ValueError("A WORKER actor must declare at least one capability")
        return self

    def has_capability(self, capability: CapabilityType) -> bool:
        """Returns whether this actor declares the given technical capability."""
        return capability in self.capabilities

    def can_be_assigned(self, capability: CapabilityType) -> bool:
        """Returns whether this actor may receive a Task requiring ``capability``.

        Assignment authority never follows from the request itself: the actor
        must be an active Worker that owns the required capability.
        """
        return self.is_active and self.role is ActorRole.WORKER and self.has_capability(capability)
