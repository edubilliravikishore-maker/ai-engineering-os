"""Actor identity for AI Engineering OS (Blueprint 4.1 #9).

Only the identity and authority attributes required by the domain rules are
modelled here. Agent runtimes, prompts, and provider integrations are outside
the domain layer entirely.
"""

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText
from ai_engineering_os.domain.enums import ActorRole, CapabilityType
from ai_engineering_os.domain.identifiers import ActorId

__all__ = ["CAPABILITY_SELECTED_ROLES", "Actor"]

CAPABILITY_SELECTED_ROLES: frozenset[ActorRole] = frozenset({ActorRole.WORKER, ActorRole.REVIEWER})
"""Roles the OS selects by capability, so each must declare at least one.

``WORKER`` from Blueprint 5.2; ``REVIEWER`` added by ADR-007 7.3. Both are
matched against a Task's ``capability``, and an Actor with none can never be
matched at all.
"""


class Actor(DomainModel):
    """A Builder, Orchestrator, Coordinator, Worker, Reviewer, or QA identity."""

    id: ActorId
    role: ActorRole
    name: NonEmptyText
    domain: NonEmptyText | None = None
    is_active: bool = True
    capabilities: frozenset[CapabilityType] = Field(default_factory=frozenset)

    @model_validator(mode="after")
    def _capability_selected_roles_must_declare_one(self) -> "Actor":
        """A role the OS selects by capability must declare at least one.

        Two roles are selected that way, and for the same reason: the OS matches
        the Task's capability against the Actor's own.

        ``WORKER`` — Blueprint 5.2 ``READY -> ASSIGNED``: "Worker ID is active
        and possesses matching capability."

        ``REVIEWER`` — ADR-007 7.3 routes a submitted Task to a Reviewer whose
        capabilities contain the Task's. A Reviewer declaring none is eligible
        for nothing, so permitting one would create an Actor the OS can never
        route work to. This **tightens** the Blueprint 4.1 #9 invariant; it
        removes no capability and changes no other role.
        """
        if self.role in CAPABILITY_SELECTED_ROLES and not self.capabilities:
            raise ValueError(f"A {self.role} actor must declare at least one capability")
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

    def can_review(self, capability: CapabilityType) -> bool:
        """Returns whether this actor may be routed a Task of ``capability`` for review.

        Mirrors :meth:`can_be_assigned` for the Reviewer side of ADR-007 7.3.
        It answers eligibility by role, activity and capability only. **Whether
        this actor performed the work is a separate question** the Rule Engine
        answers from the Task and its Revisions, because an Actor cannot know it
        from its own attributes.
        """
        return (
            self.is_active and self.role is ActorRole.REVIEWER and self.has_capability(capability)
        )
