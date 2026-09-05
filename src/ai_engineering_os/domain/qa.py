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
    TaskId,
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

    **Scope is an association, never a declaration (ADR-003 3.11, ADR-004 4.8).**
    A defect records the entity it was found against; the OS derives acceptance
    impact by resolving that association. There is deliberately no ``in_scope``
    boolean, because a QA self-assessment is never accepted as the authority.

    | ``scope_task_id`` | ``scope_feature_id`` | Meaning                        |
    | :---------------- | :------------------- | :----------------------------- |
    | set               | unset                | Resolves ``Defect -> Task -> Feature`` |
    | unset             | set                  | Resolves ``Defect -> Feature``  |
    | unset             | unset                | Scope unresolved — valid to record |
    | set               | set                  | Rejected at construction        |

    Recording a defect with no association stays valid on purpose: ADR-003 3.11's
    "scope unresolved" path must be constructible, or the rule that must reject it
    could never be exercised. Resolution itself is performed by the Rule Engine
    against supplied facts, never by this model.
    """

    id: QADefectId
    title: NonEmptyText
    severity: NonEmptyText
    priority: NonEmptyText
    is_blocker: bool = False
    status: DefectStatus = DefectStatus.OPEN
    scope_task_id: TaskId | None = None
    scope_feature_id: FeatureId | None = None

    @model_validator(mode="after")
    def _scope_association_must_be_singular(self) -> "QADefect":
        """A defect is found against a Task or a Feature, never both (ADR-004 4.8)."""
        if self.scope_task_id is not None and self.scope_feature_id is not None:
            raise ValueError(
                "A QA defect cannot associate with both a Task and a Feature; "
                "a Task association already resolves to its Feature"
            )
        return self

    @property
    def is_unresolved(self) -> bool:
        """Returns whether this defect still blocks Feature Acceptance."""
        return self.status is DefectStatus.OPEN


class QAReport(DomainModel):
    """A structured, machine-first QA verification record.

    ``qa_round`` records **which build-and-check cycle of the Feature this report
    belongs to** (ADR-007 7.4). It is stamped by the Kernel from the Feature's
    own current round at the moment the report is recorded — never supplied by
    the reporting Actor and never derived from a clock — so a report written
    during one round but submitted after rework began stays in the round it was
    written for.

    A report is never edited, so its round never changes. Reports from earlier
    rounds remain readable history and are never re-evaluated as the Feature's
    current defect position.
    """

    id: QAReportId
    feature_id: FeatureId
    status: QAStatus
    qa_round: int = Field(default=1, ge=1)
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
