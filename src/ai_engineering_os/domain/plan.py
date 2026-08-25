"""Feature Plan and planned Task definitions (Blueprint 4.1 #2, Design Session 009).

The Coordinator owns the Feature Plan: required capabilities, the task
breakdown, and the dependency graph. Plans are revised additively; a plan is
never silently overwritten.
"""

from datetime import datetime

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, Slug, utc_now
from ai_engineering_os.domain.enums import CapabilityType, PlanStatus
from ai_engineering_os.domain.identifiers import ActorId, FeatureId, FeaturePlanId

__all__ = ["FeaturePlan", "TaskDefinition"]


class TaskDefinition(DomainModel):
    """A planned Task inside a Feature Plan.

    ``key`` is a plan-local reference. Dependencies are declared between plan
    keys because OS Task identities do not exist until the plan is activated.
    """

    key: Slug
    title: NonEmptyText
    capability: CapabilityType
    depends_on: tuple[Slug, ...] = ()

    @model_validator(mode="after")
    def _dependencies_must_be_well_formed(self) -> "TaskDefinition":
        if self.key in self.depends_on:
            raise ValueError(f"Task definition {self.key!r} cannot depend on itself")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError(f"Task definition {self.key!r} declares duplicate dependencies")
        return self


class FeaturePlan(DomainModel):
    """The Coordinator's plan for delivering a Feature."""

    id: FeaturePlanId
    feature_id: FeatureId
    revision_number: int = Field(ge=1)
    created_by: ActorId
    status: PlanStatus = PlanStatus.DRAFT
    required_capabilities: tuple[CapabilityType, ...] = ()
    task_definitions: tuple[TaskDefinition, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _capabilities_must_be_unique(self) -> "FeaturePlan":
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise ValueError("Feature Plan declares duplicate required capabilities")
        return self

    @model_validator(mode="after")
    def _task_keys_must_be_unique(self) -> "FeaturePlan":
        keys = [definition.key for definition in self.task_definitions]
        if len(set(keys)) != len(keys):
            raise ValueError("Feature Plan declares duplicate task definition keys")
        return self

    @model_validator(mode="after")
    def _dependencies_must_resolve(self) -> "FeaturePlan":
        keys = {definition.key for definition in self.task_definitions}
        for definition in self.task_definitions:
            unknown = sorted(set(definition.depends_on) - keys)
            if unknown:
                raise ValueError(
                    f"Task definition {definition.key!r} depends on unknown keys: {unknown}"
                )
        return self

    @model_validator(mode="after")
    def _dependency_graph_must_be_acyclic(self) -> "FeaturePlan":
        cycle = _find_cycle({d.key: d.depends_on for d in self.task_definitions})
        if cycle is not None:
            raise ValueError(f"Feature Plan dependency graph contains a cycle: {cycle}")
        return self

    @model_validator(mode="after")
    def _capabilities_must_cover_tasks(self) -> "FeaturePlan":
        declared = set(self.required_capabilities)
        missing = sorted({d.capability for d in self.task_definitions} - declared)
        if missing:
            raise ValueError(f"Feature Plan omits required capabilities: {missing}")
        return self

    @model_validator(mode="after")
    def _non_draft_plan_needs_tasks(self) -> "FeaturePlan":
        """Blueprint 5.1: a Feature Plan must define at least one Task to leave DRAFT."""
        if self.status is not PlanStatus.DRAFT and not self.task_definitions:
            raise ValueError(
                f"A Feature Plan in status {self.status} must declare at least one task definition"
            )
        return self

    @property
    def dependency_free_keys(self) -> tuple[str, ...]:
        """Plan keys with no prerequisites; these become READY on activation."""
        return tuple(d.key for d in self.task_definitions if not d.depends_on)

    def definition(self, key: str) -> TaskDefinition | None:
        """Returns the task definition registered under ``key``, if any."""
        return next((d for d in self.task_definitions if d.key == key), None)

    def with_status(self, status: PlanStatus) -> "FeaturePlan":
        """Returns a new Feature Plan carrying ``status``."""
        return self._evolve(status=status)


def _find_cycle(graph: dict[str, tuple[str, ...]]) -> list[str] | None:
    """Returns the first dependency cycle found in ``graph``, or None."""
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def walk(node: str) -> list[str] | None:
        if node in visited:
            return None
        if node in visiting:
            return [*path[path.index(node) :], node]
        visiting.add(node)
        path.append(node)
        for dependency in graph.get(node, ()):
            cycle = walk(dependency)
            if cycle is not None:
                return cycle
        path.pop()
        visiting.discard(node)
        visited.add(node)
        return None

    for key in graph:
        cycle = walk(key)
        if cycle is not None:
            return cycle
    return None
