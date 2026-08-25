"""Domain enumerations for AI Engineering OS.

Every enumeration here is transcribed from the frozen architecture (Design
Sessions 001-009) and the Foundation v1 Implementation Blueprint. No lifecycle
state is added for convenience.
"""

from enum import StrEnum

__all__ = [
    "ActorRole",
    "CapabilityType",
    "DecisionScope",
    "DefectStatus",
    "EvidenceSourceType",
    "EvidenceType",
    "FeatureStatus",
    "Initiator",
    "PlanStatus",
    "QAStatus",
    "ReviewOutcome",
    "SystemActor",
    "TaskStatus",
    "WorkPackageStatus",
]


class ActorRole(StrEnum):
    """Roles that may act inside AI Engineering OS (Blueprint 4.1 #9)."""

    BUILDER = "BUILDER"
    ORCHESTRATOR = "ORCHESTRATOR"
    COORDINATOR = "COORDINATOR"
    WORKER = "WORKER"
    REVIEWER = "REVIEWER"
    QA = "QA"


class SystemActor(StrEnum):
    """The OS itself acting as the initiator of a transition.

    Several blueprint transitions declare ``OS`` as the requester (for example
    ``CREATED -> READY``). The OS is infrastructure rather than an agent, so it
    is deliberately kept out of :class:`ActorRole`.
    """

    OS = "OS"


type Initiator = ActorRole | SystemActor
"""Anything permitted to request a lifecycle transition."""


class CapabilityType(StrEnum):
    """Technical capabilities a Worker may own (Design Sessions 001-002)."""

    BACKEND = "BACKEND"
    FRONTEND = "FRONTEND"
    QA = "QA"


class FeatureStatus(StrEnum):
    """Feature lifecycle states (Blueprint 5.1)."""

    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    IN_VALIDATION = "IN_VALIDATION"
    ACCEPTED = "ACCEPTED"


class PlanStatus(StrEnum):
    """Feature Plan lifecycle states (Design Session 009)."""

    DRAFT = "DRAFT"
    READY = "READY"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SUPERSEDED = "SUPERSEDED"


class TaskStatus(StrEnum):
    """Task lifecycle states (Blueprint 5.2)."""

    CREATED = "CREATED"
    PENDING_DEPENDENCIES = "PENDING_DEPENDENCIES"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"
    IN_QA = "IN_QA"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    ACCEPTED = "ACCEPTED"


class WorkPackageStatus(StrEnum):
    """Work Package lifecycle states (Blueprint 5.3)."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    REVIEWED = "REVIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class EvidenceSourceType(StrEnum):
    """Evidence origin (Design Session 005)."""

    SYSTEM = "SYSTEM"
    WORKER = "WORKER"


class EvidenceType(StrEnum):
    """Evidence kinds recognised by the OS (Blueprint 4.1 #6)."""

    GIT_DIFF = "GIT_DIFF"
    TEST_OUTPUT = "TEST_OUTPUT"
    API_RESPONSE = "API_RESPONSE"
    BUILD_LOG = "BUILD_LOG"
    DB_VERIFICATION = "DB_VERIFICATION"
    REASONING = "REASONING"


class QAStatus(StrEnum):
    """Overall QA Report outcome (Blueprint 4.1 #7)."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class DefectStatus(StrEnum):
    """QA defect resolution marker.

    Design Session 009 requires "zero unresolved in-scope defects" before
    Feature Acceptance, which is the distinction modelled here.
    """

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class ReviewOutcome(StrEnum):
    """Reviewer decision outcomes (Blueprint 5.2 and event model)."""

    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class DecisionScope(StrEnum):
    """Authority scope of a recorded Decision (Blueprint 4.1 #8)."""

    FEATURE = "FEATURE"
    SYSTEM = "SYSTEM"
    BUSINESS = "BUSINESS"
