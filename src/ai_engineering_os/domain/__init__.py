"""Pure domain layer for AI Engineering OS.

This package contains domain entities, value objects, enumerations, and
invariants only. It has no FastAPI, SQLAlchemy, PostgreSQL, filesystem, or
network dependency and is independently unit-testable.
"""

from ai_engineering_os.domain.actor import Actor
from ai_engineering_os.domain.base import (
    DomainModel,
    NonEmptyText,
    Sha256Hex,
    Slug,
    utc_now,
)
from ai_engineering_os.domain.decision import (
    DECISION_AUTHORITY,
    Decision,
    DecisionAcknowledgement,
    ReviewDecision,
)
from ai_engineering_os.domain.enums import (
    ActorRole,
    CapabilityType,
    DecisionScope,
    DefectStatus,
    EvidenceSourceType,
    EvidenceType,
    FeatureStatus,
    Initiator,
    PlanStatus,
    QAStatus,
    ReviewOutcome,
    SystemActor,
    TaskStatus,
    WorkPackageStatus,
)
from ai_engineering_os.domain.errors import (
    DomainError,
    ImmutableRecordError,
    InvariantViolationError,
    RevisionSequenceError,
    StateMachineDefinitionError,
)
from ai_engineering_os.domain.evidence import (
    EvidenceMetadata,
    EvidenceRecord,
    sha256_hex,
)
from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.identifiers import (
    ActorId,
    ClaimId,
    DecisionId,
    EvidenceId,
    FeatureId,
    FeaturePlanId,
    QADefectId,
    QAReportId,
    ReviewDecisionId,
    TaskId,
    TaskRevisionId,
    WorkPackageId,
    new_id,
)
from ai_engineering_os.domain.plan import FeaturePlan, TaskDefinition
from ai_engineering_os.domain.qa import QADefect, QAReport, TestResult
from ai_engineering_os.domain.task import Task, TaskRevision, TaskRevisionHistory
from ai_engineering_os.domain.work_package import Claim, VerificationGuide, WorkPackage

__all__ = [
    "DECISION_AUTHORITY",
    "Actor",
    "ActorId",
    "ActorRole",
    "CapabilityType",
    "Claim",
    "ClaimId",
    "Decision",
    "DecisionAcknowledgement",
    "DecisionId",
    "DecisionScope",
    "DefectStatus",
    "DomainError",
    "DomainModel",
    "EvidenceId",
    "EvidenceMetadata",
    "EvidenceRecord",
    "EvidenceSourceType",
    "EvidenceType",
    "Feature",
    "FeatureId",
    "FeaturePlan",
    "FeaturePlanId",
    "FeatureStatus",
    "ImmutableRecordError",
    "Initiator",
    "InvariantViolationError",
    "NonEmptyText",
    "PlanStatus",
    "QADefect",
    "QADefectId",
    "QAReport",
    "QAReportId",
    "QAStatus",
    "ReviewDecision",
    "ReviewDecisionId",
    "ReviewOutcome",
    "RevisionSequenceError",
    "Sha256Hex",
    "Slug",
    "StateMachineDefinitionError",
    "SystemActor",
    "Task",
    "TaskDefinition",
    "TaskId",
    "TaskRevision",
    "TaskRevisionHistory",
    "TaskRevisionId",
    "TaskStatus",
    "TestResult",
    "VerificationGuide",
    "WorkPackage",
    "WorkPackageId",
    "WorkPackageStatus",
    "new_id",
    "sha256_hex",
    "utc_now",
]
