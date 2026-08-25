"""QA Report, test results, and defects (Blueprint 4.1 #7, Design Session 009).

QA reports behavioural validation. QA never performs Feature Acceptance; the
Coordinator retains that authority.
"""

from datetime import datetime

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, utc_now
from ai_engineering_os.domain.enums import DefectStatus, QAStatus
from ai_engineering_os.domain.identifiers import (
    EvidenceId,
    FeatureId,
    QADefectId,
    QAReportId,
    TaskRevisionId,
)

__all__ = ["QADefect", "QAReport", "TestResult"]


class TestResult(DomainModel):
    """One executed test case recorded inside a QA Report."""

    name: NonEmptyText
    passed: bool
    details: NonEmptyText | None = None


class QADefect(DomainModel):
    """A defect discovered by QA.

    Severity and Priority are recorded as labels: Design Session 004 explicitly
    leaves the classification system open, so no scale is invented here.
    """

    id: QADefectId
    title: NonEmptyText
    severity: NonEmptyText
    priority: NonEmptyText
    is_blocker: bool = False
    status: DefectStatus = DefectStatus.OPEN

    @property
    def is_unresolved(self) -> bool:
        """Returns whether this defect still blocks Feature Acceptance."""
        return self.status is DefectStatus.OPEN


class QAReport(DomainModel):
    """A structured, machine-first QA verification record."""

    id: QAReportId
    feature_id: FeatureId
    status: QAStatus
    task_revision_id: TaskRevisionId | None = None
    is_final_pass: bool = False
    tested_scope: tuple[NonEmptyText, ...] = ()
    results: tuple[TestResult, ...] = ()
    defects: tuple[QADefect, ...] = ()
    evidence_ids: tuple[EvidenceId, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _identifiers_must_be_unique(self) -> "QAReport":
        defect_ids = [defect.id for defect in self.defects]
        if len(set(defect_ids)) != len(defect_ids):
            raise ValueError("A QA Report cannot record duplicate defect identifiers")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("A QA Report cannot record duplicate Evidence identifiers")
        return self

    @model_validator(mode="after")
    def _status_must_match_findings(self) -> "QAReport":
        if self.status is QAStatus.PASSED and self.unresolved_defects:
            raise ValueError("A PASSED QA Report cannot carry unresolved defects")
        if self.status is QAStatus.FAILED and not self.defects:
            raise ValueError("A FAILED QA Report must record at least one defect")
        if self.status is QAStatus.BLOCKED and not self.blocking_defects:
            raise ValueError("A BLOCKED QA Report must record at least one blocking defect")
        return self

    @model_validator(mode="after")
    def _final_pass_must_be_evidenced(self) -> "QAReport":
        """A QA Final Pass certifies a tested scope, so it cannot be empty."""
        if self.is_final_pass and (not self.tested_scope or not self.results):
            raise ValueError("A QA Final Pass must record its tested scope and test results")
        return self

    @property
    def unresolved_defects(self) -> tuple[QADefect, ...]:
        """Defects that are still OPEN."""
        return tuple(defect for defect in self.defects if defect.is_unresolved)

    @property
    def blocking_defects(self) -> tuple[QADefect, ...]:
        """Unresolved defects flagged as blockers."""
        return tuple(defect for defect in self.unresolved_defects if defect.is_blocker)

    @property
    def is_valid_final_pass(self) -> bool:
        """Design Session 009: a valid Final Pass passed with zero unresolved defects."""
        return self.is_final_pass and self.status is QAStatus.PASSED and not self.unresolved_defects
