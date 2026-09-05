"""Feature domain entity (Blueprint 4.1 #1, Design Session 009)."""

from datetime import datetime

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, Slug, utc_now
from ai_engineering_os.domain.enums import FeatureStatus
from ai_engineering_os.domain.identifiers import ActorId, FeatureId

__all__ = ["Feature"]


class Feature(DomainModel):
    """A user or business capability requested by the Builder.

    A Feature is the unit of delivery. It is owned by exactly one Coordinator
    and carries the recorded scope boundary the OS enforces during acceptance.
    """

    id: FeatureId
    slug: Slug
    title: NonEmptyText
    goal: NonEmptyText
    coordinator_id: ActorId
    status: FeatureStatus = FeatureStatus.DRAFT
    requirements: tuple[NonEmptyText, ...] = ()
    in_scope: tuple[NonEmptyText, ...] = ()
    out_of_scope: tuple[NonEmptyText, ...] = ()
    acceptance_criteria: tuple[NonEmptyText, ...] = ()
    qa_round: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _scope_must_not_overlap(self) -> "Feature":
        """Recorded scope boundaries must be unambiguous (Design Session 009)."""
        overlap = sorted(set(self.in_scope) & set(self.out_of_scope))
        if overlap:
            raise ValueError(f"Feature scope entries cannot be both in and out of scope: {overlap}")
        return self

    @model_validator(mode="after")
    def _planned_feature_needs_acceptance_criteria(self) -> "Feature":
        """QA validates against acceptance criteria, so they must exist past DRAFT."""
        if self.status is not FeatureStatus.DRAFT and not self.acceptance_criteria:
            raise ValueError(
                f"A Feature in status {self.status} must declare at least one acceptance criterion"
            )
        return self

    @model_validator(mode="after")
    def _timestamps_must_be_ordered(self) -> "Feature":
        if self.updated_at < self.created_at:
            raise ValueError("Feature updated_at cannot precede created_at")
        return self

    def is_in_scope(self, capability: str) -> bool:
        """Returns whether a capability is inside the Feature's recorded scope."""
        return capability in self.in_scope

    def with_status(self, status: FeatureStatus, *, at: datetime | None = None) -> "Feature":
        """Returns a new Feature carrying ``status``. The original is untouched."""
        return self._evolve(status=status, updated_at=at or utc_now())

    def opening_next_qa_round(self, *, at: datetime | None = None) -> "Feature":
        """Returns a new IN_PROGRESS Feature whose QA round has advanced by one.

        The rework loop and the increment are **one operation**, expressed as one
        method, because ADR-007 7.4 makes correctness depend on the round
        advancing on exactly that transition and on no other. Separating them
        would leave two calls a caller could make independently.

        This is the **only** way a Feature's ``qa_round`` changes. Nothing
        decrements it, and no other transition touches it.
        """
        return self._evolve(
            status=FeatureStatus.IN_PROGRESS,
            qa_round=self.qa_round + 1,
            updated_at=at or utc_now(),
        )
