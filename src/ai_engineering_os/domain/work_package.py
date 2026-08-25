"""Work Package, Claims, and Verification Guide (Blueprint 4.1 #5, DS-003/005/006).

A Work Package is the machine-first handover object between engineering stages.
Once submitted it is immutable: no actor, including the authoring Worker, may
edit it. Fixes are expressed as a new Revision carrying a new Work Package.
"""

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText
from ai_engineering_os.domain.enums import WorkPackageStatus
from ai_engineering_os.domain.errors import ImmutableRecordError
from ai_engineering_os.domain.identifiers import ClaimId, TaskRevisionId, WorkPackageId

__all__ = ["Claim", "VerificationGuide", "WorkPackage"]


class Claim(DomainModel):
    """A statement the Worker makes about the delivered work.

    Design Session 005: every Claim requires matching, relevant Evidence.
    """

    id: ClaimId
    claim_type: NonEmptyText
    description: NonEmptyText


class VerificationGuide(DomainModel):
    """How downstream stages verify the implementation (Design Session 006)."""

    steps: tuple[NonEmptyText, ...] = Field(min_length=1)
    endpoints: tuple[NonEmptyText, ...] = ()
    expected_outputs: tuple[NonEmptyText, ...] = ()


class WorkPackage(DomainModel):
    """The Worker's structured handover object for one Task Revision."""

    id: WorkPackageId
    task_revision_id: TaskRevisionId
    summary: NonEmptyText
    status: WorkPackageStatus = WorkPackageStatus.DRAFT
    claims: tuple[Claim, ...] = ()
    verification_guide: VerificationGuide | None = None
    worker_notes: tuple[NonEmptyText, ...] = ()
    risks: NonEmptyText | None = None
    submitted_at: datetime | None = None

    @model_validator(mode="after")
    def _claim_ids_must_be_unique(self) -> "WorkPackage":
        ids = [claim.id for claim in self.claims]
        if len(set(ids)) != len(ids):
            raise ValueError("A Work Package cannot declare duplicate Claim identifiers")
        return self

    @model_validator(mode="after")
    def _submitted_package_must_be_complete(self) -> "WorkPackage":
        """Blueprint 5.2: submission requires Claims and a Verification Guide."""
        if self.status is WorkPackageStatus.DRAFT:
            if self.submitted_at is not None:
                raise ValueError("A DRAFT Work Package cannot record a submission timestamp")
            return self
        if not self.claims:
            raise ValueError(f"A {self.status} Work Package must declare at least one Claim")
        if self.verification_guide is None:
            raise ValueError(f"A {self.status} Work Package must carry a Verification Guide")
        if self.submitted_at is None:
            raise ValueError(f"A {self.status} Work Package must record a submission timestamp")
        return self

    @property
    def is_draft(self) -> bool:
        """Returns whether this Work Package is still Worker-local editable content."""
        return self.status is WorkPackageStatus.DRAFT

    @property
    def is_immutable(self) -> bool:
        """Returns whether the recorded content of this Work Package is frozen."""
        return not self.is_draft

    def revise_draft(self, **changes: Any) -> "WorkPackage":
        """Returns an updated DRAFT Work Package.

        Raises:
            ImmutableRecordError: if the Work Package has already been submitted,
                or if the caller attempts to change the lifecycle status here.
        """
        if self.is_immutable:
            raise ImmutableRecordError(
                f"A {self.status} Work Package cannot be edited; produce a new Revision instead",
                record_type="WorkPackage",
                operation="revise_draft",
            )
        if "status" in changes:
            raise ImmutableRecordError(
                "Work Package lifecycle status changes must go through with_status",
                record_type="WorkPackage",
                operation="revise_draft",
            )
        return self._evolve(**changes)

    def with_status(self, status: WorkPackageStatus) -> "WorkPackage":
        """Returns a new Work Package carrying ``status``; recorded content is unchanged."""
        return self._evolve(status=status)

    def submit(self, *, at: datetime) -> "WorkPackage":
        """Returns the SUBMITTED, immutable form of this DRAFT Work Package."""
        if self.is_immutable:
            raise ImmutableRecordError(
                f"A {self.status} Work Package has already been submitted",
                record_type="WorkPackage",
                operation="submit",
            )
        return self._evolve(status=WorkPackageStatus.SUBMITTED, submitted_at=at)
