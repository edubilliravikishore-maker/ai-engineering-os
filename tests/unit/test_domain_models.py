"""Unit tests for pure domain models and their invariants."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    Claim,
    ClaimId,
    Decision,
    DecisionId,
    DecisionScope,
    DefectStatus,
    EvidenceId,
    EvidenceRecord,
    EvidenceSourceType,
    EvidenceType,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
    FeatureStatus,
    PlanStatus,
    QADefect,
    QADefectId,
    QAReport,
    QAReportId,
    QAStatus,
    ReviewDecision,
    ReviewDecisionId,
    ReviewOutcome,
    Task,
    TaskDefinition,
    TaskId,
    TaskRevision,
    TaskRevisionId,
    TaskStatus,
    VerificationGuide,
    WorkPackage,
    WorkPackageStatus,
    new_id,
    sha256_hex,
    utc_now,
)
from ai_engineering_os.domain.qa import TestResult as QATestResult

# --------------------------------------------------------------------------
# Identifiers
# --------------------------------------------------------------------------


def test_identifiers_are_distinct_values() -> None:
    """Verifies generated identifiers are unique per call."""
    assert new_id(FeatureId) != new_id(FeatureId)


def test_model_rejects_a_non_uuid_identifier() -> None:
    """Verifies domain models reject malformed identifier data."""
    with pytest.raises(ValidationError):
        Task(
            id="not-a-uuid",
            feature_id=new_id(FeatureId),
            title="Implement Auth API",
            capability=CapabilityType.BACKEND,
        )


# --------------------------------------------------------------------------
# Actor
# --------------------------------------------------------------------------


def test_worker_must_declare_a_capability() -> None:
    """Verifies a Worker is selected by capability (Blueprint 5.2 READY -> ASSIGNED)."""
    with pytest.raises(ValidationError, match="at least one capability"):
        Actor(id=new_id(ActorId), role=ActorRole.WORKER, name="worker-without-capability")


def test_coordinator_does_not_need_a_capability() -> None:
    """Verifies non-Worker roles are not capability-selected."""
    coordinator = Actor(id=new_id(ActorId), role=ActorRole.COORDINATOR, name="auth-coordinator")
    assert coordinator.capabilities == frozenset()


def test_only_an_active_matching_worker_can_be_assigned(backend_worker: Actor) -> None:
    """Verifies assignment authority never follows from the request itself."""
    assert backend_worker.can_be_assigned(CapabilityType.BACKEND)
    assert not backend_worker.can_be_assigned(CapabilityType.FRONTEND)
    assert not backend_worker._evolve(is_active=False).can_be_assigned(CapabilityType.BACKEND)


def test_a_coordinator_can_never_be_assigned_a_task() -> None:
    """Verifies a non-Worker role cannot receive implementation work."""
    coordinator = Actor(id=new_id(ActorId), role=ActorRole.COORDINATOR, name="auth-coordinator")
    assert not coordinator.can_be_assigned(CapabilityType.BACKEND)


# --------------------------------------------------------------------------
# Feature
# --------------------------------------------------------------------------


def test_feature_defaults_to_draft(feature: Feature) -> None:
    """Verifies a newly recorded Feature starts in DRAFT."""
    assert feature.status is FeatureStatus.DRAFT


def test_feature_scope_cannot_overlap(coordinator_id: ActorId) -> None:
    """Verifies the recorded scope boundary is unambiguous (Design Session 009)."""
    with pytest.raises(ValidationError, match="both in and out of scope"):
        Feature(
            id=new_id(FeatureId),
            slug="user-authentication",
            title="Auth",
            goal="Sign in",
            coordinator_id=coordinator_id,
            in_scope=("Google OAuth",),
            out_of_scope=("Google OAuth",),
        )


def test_feature_beyond_draft_requires_acceptance_criteria(coordinator_id: ActorId) -> None:
    """Verifies QA always has agreed acceptance criteria to validate against."""
    with pytest.raises(ValidationError, match="acceptance criterion"):
        Feature(
            id=new_id(FeatureId),
            slug="user-authentication",
            title="Auth",
            goal="Sign in",
            coordinator_id=coordinator_id,
            status=FeatureStatus.PLANNED,
        )


@pytest.mark.parametrize("slug", ["User-Auth", "user auth", "user_auth", "-user", ""])
def test_feature_rejects_a_malformed_slug(coordinator_id: ActorId, slug: str) -> None:
    """Verifies domain models reject invalid identifying data."""
    with pytest.raises(ValidationError):
        Feature(
            id=new_id(FeatureId),
            slug=slug,
            title="Auth",
            goal="Sign in",
            coordinator_id=coordinator_id,
        )


def test_feature_rejects_blank_title(coordinator_id: ActorId) -> None:
    """Verifies whitespace-only text is rejected."""
    with pytest.raises(ValidationError):
        Feature(
            id=new_id(FeatureId),
            slug="user-authentication",
            title="   ",
            goal="Sign in",
            coordinator_id=coordinator_id,
        )


def test_feature_rejects_updated_before_created(feature: Feature) -> None:
    """Verifies timestamps cannot describe an impossible history."""
    with pytest.raises(ValidationError, match="cannot precede"):
        feature._evolve(updated_at=feature.created_at - timedelta(seconds=1))


def test_feature_rejects_unknown_fields(feature: Feature) -> None:
    """Verifies domain models refuse undeclared data."""
    with pytest.raises(ValidationError):
        Feature(**{**feature.model_dump(), "priority": "HIGH"})


# --------------------------------------------------------------------------
# Feature Plan
# --------------------------------------------------------------------------


def test_plan_reports_dependency_free_tasks(feature_plan: FeaturePlan) -> None:
    """Verifies dependency-free plan keys are identifiable for activation."""
    assert feature_plan.dependency_free_keys == ("auth-api",)
    assert feature_plan.definition("auth-qa") is not None
    assert feature_plan.definition("missing") is None


def test_plan_rejects_duplicate_task_keys(feature: Feature, coordinator_id: ActorId) -> None:
    """Verifies plan-local task keys uniquely identify a planned Task."""
    definition = TaskDefinition(key="auth-api", title="Auth API", capability=CapabilityType.BACKEND)
    with pytest.raises(ValidationError, match="duplicate task definition keys"):
        FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=1,
            created_by=coordinator_id,
            required_capabilities=(CapabilityType.BACKEND,),
            task_definitions=(definition, definition),
        )


def test_plan_rejects_unknown_dependency(feature: Feature, coordinator_id: ActorId) -> None:
    """Verifies Blueprint 5.1: invalid dependencies block plan activation."""
    with pytest.raises(ValidationError, match="unknown keys"):
        FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=1,
            created_by=coordinator_id,
            required_capabilities=(CapabilityType.BACKEND,),
            task_definitions=(
                TaskDefinition(
                    key="auth-api",
                    title="Auth API",
                    capability=CapabilityType.BACKEND,
                    depends_on=("does-not-exist",),
                ),
            ),
        )


def test_plan_rejects_a_dependency_cycle(feature: Feature, coordinator_id: ActorId) -> None:
    """Verifies a task breakdown cannot declare an unexecutable dependency cycle."""
    with pytest.raises(ValidationError, match="cycle"):
        FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=1,
            created_by=coordinator_id,
            required_capabilities=(CapabilityType.BACKEND,),
            task_definitions=(
                TaskDefinition(
                    key="a", title="A", capability=CapabilityType.BACKEND, depends_on=("b",)
                ),
                TaskDefinition(
                    key="b", title="B", capability=CapabilityType.BACKEND, depends_on=("a",)
                ),
            ),
        )


def test_task_definition_cannot_depend_on_itself() -> None:
    """Verifies a planned Task cannot block its own execution."""
    with pytest.raises(ValidationError, match="cannot depend on itself"):
        TaskDefinition(
            key="auth-api",
            title="Auth API",
            capability=CapabilityType.BACKEND,
            depends_on=("auth-api",),
        )


def test_plan_must_declare_the_capabilities_it_requires(
    feature: Feature, coordinator_id: ActorId
) -> None:
    """Verifies the Coordinator identifies required capabilities (Design Session 007)."""
    with pytest.raises(ValidationError, match="omits required capabilities"):
        FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=1,
            created_by=coordinator_id,
            required_capabilities=(CapabilityType.BACKEND,),
            task_definitions=(
                TaskDefinition(key="auth-ui", title="Auth UI", capability=CapabilityType.FRONTEND),
            ),
        )


def test_plan_beyond_draft_needs_task_definitions(
    feature: Feature, coordinator_id: ActorId
) -> None:
    """Verifies Blueprint 5.1: an empty task list cannot leave DRAFT."""
    with pytest.raises(ValidationError, match="at least one task definition"):
        FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=1,
            created_by=coordinator_id,
            status=PlanStatus.READY,
        )


def test_plan_revision_number_starts_at_one(feature: Feature, coordinator_id: ActorId) -> None:
    """Verifies plan revisions are numbered from one."""
    with pytest.raises(ValidationError):
        FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=0,
            created_by=coordinator_id,
        )


# --------------------------------------------------------------------------
# Task
# --------------------------------------------------------------------------


def test_task_cannot_depend_on_itself(feature: Feature) -> None:
    """Verifies a Task cannot make itself unexecutable."""
    task_id = new_id(TaskId)
    with pytest.raises(ValidationError, match="cannot depend on itself"):
        Task(
            id=task_id,
            feature_id=feature.id,
            title="Auth API",
            capability=CapabilityType.BACKEND,
            dependencies=(task_id,),
        )


def test_pending_dependencies_requires_declared_dependencies(task: Task) -> None:
    """Verifies Blueprint 5.2 rejects PENDING_DEPENDENCIES with no dependency."""
    with pytest.raises(ValidationError, match="at least one dependency"):
        task.with_status(TaskStatus.PENDING_DEPENDENCIES)


def test_unassigned_task_cannot_record_a_worker(task: Task, worker_id: ActorId) -> None:
    """Verifies a Worker is only recorded from ASSIGNED onwards."""
    with pytest.raises(ValidationError, match="cannot record an assigned Worker"):
        task._evolve(status=TaskStatus.READY, assigned_worker_id=worker_id)


def test_assigned_task_must_record_a_worker(task: Task) -> None:
    """Verifies a Task cannot claim to be assigned without a Worker."""
    with pytest.raises(ValidationError, match="must record an assigned Worker"):
        task.with_status(TaskStatus.ASSIGNED)


def test_post_submission_task_requires_an_active_revision(task: Task, worker_id: ActorId) -> None:
    """Verifies SUBMITTED and beyond always point at a Revision."""
    assigned = task.with_status(TaskStatus.READY).assign(worker_id)
    with pytest.raises(ValidationError, match="must have an active Revision"):
        assigned.with_status(TaskStatus.SUBMITTED)


def test_task_assignment_records_the_worker(task: Task, worker_id: ActorId) -> None:
    """Verifies assignment binds exactly one Worker to the Task."""
    assigned = task.with_status(TaskStatus.READY).assign(worker_id)
    assert assigned.status is TaskStatus.ASSIGNED
    assert assigned.is_assigned_to(worker_id)
    assert not assigned.is_assigned_to(new_id(ActorId))


def test_unassigned_task_is_assigned_to_nobody(task: Task) -> None:
    """Verifies an unassigned Task never matches an actor identity."""
    assert not task.is_assigned_to(new_id(ActorId))


# --------------------------------------------------------------------------
# Work Package
# --------------------------------------------------------------------------


def test_submitted_work_package_requires_claims_and_a_guide(
    draft_work_package: WorkPackage,
) -> None:
    """Verifies Blueprint 5.2: submission requires Claims and a Verification Guide."""
    with pytest.raises(ValidationError, match="at least one Claim"):
        draft_work_package._evolve(status=WorkPackageStatus.SUBMITTED, submitted_at=utc_now())


def test_submitted_work_package_requires_a_verification_guide(
    draft_work_package: WorkPackage, claim: Claim, feature: Feature
) -> None:
    """Verifies the Verification Guide is mandatory once submitted."""
    with pytest.raises(ValidationError, match="Verification Guide"):
        draft_work_package._evolve(
            status=WorkPackageStatus.SUBMITTED,
            claims=(claim,),
            submitted_at=feature.created_at,
        )


def test_draft_work_package_cannot_record_submission_time(
    draft_work_package: WorkPackage, feature: Feature
) -> None:
    """Verifies a DRAFT package is Worker-local and not yet a system record."""
    with pytest.raises(ValidationError, match="cannot record a submission timestamp"):
        draft_work_package._evolve(submitted_at=feature.created_at)


def test_work_package_rejects_duplicate_claims(
    draft_work_package: WorkPackage, claim: Claim
) -> None:
    """Verifies Claims are uniquely identifiable for Evidence mapping."""
    with pytest.raises(ValidationError, match="duplicate Claim"):
        draft_work_package.revise_draft(claims=(claim, claim))


def test_verification_guide_requires_at_least_one_step() -> None:
    """Verifies Design Session 006: the guide must reduce downstream ambiguity."""
    with pytest.raises(ValidationError):
        VerificationGuide(steps=())


def test_claim_requires_type_and_description() -> None:
    """Verifies a Claim is never empty."""
    with pytest.raises(ValidationError):
        Claim(id=new_id(ClaimId), claim_type="", description="Login API implemented")


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------


def test_evidence_checksum_verifies_integrity(system_evidence: EvidenceRecord) -> None:
    """Verifies Evidence records preserve integrity verification."""
    assert system_evidence.checksum == sha256_hex("diff --git a/auth.py b/auth.py")
    assert system_evidence.verify_integrity("diff --git a/auth.py b/auth.py")
    assert not system_evidence.verify_integrity("tampered content")


def test_evidence_rejects_a_malformed_checksum(draft_work_package: WorkPackage) -> None:
    """Verifies only a well-formed SHA-256 digest is accepted."""
    with pytest.raises(ValidationError):
        EvidenceRecord(
            id=new_id(EvidenceId),
            source_type=EvidenceSourceType.SYSTEM,
            evidence_type=EvidenceType.TEST_OUTPUT,
            content="10 passed",
            checksum="not-a-digest",
            work_package_id=draft_work_package.id,
        )


def test_evidence_must_reference_a_work_package_or_qa_report() -> None:
    """Verifies Evidence always supports a Claim or a QA result."""
    with pytest.raises(ValidationError, match="Work Package or a QA Report"):
        EvidenceRecord.for_inline_content(
            id=new_id(EvidenceId),
            source_type=EvidenceSourceType.SYSTEM,
            evidence_type=EvidenceType.BUILD_LOG,
            content="build ok",
        )


def test_worker_evidence_cannot_claim_os_verification(
    draft_work_package: WorkPackage,
) -> None:
    """Verifies Design Session 005: only independent evidence is OS-verified."""
    with pytest.raises(ValidationError, match="independently verified"):
        EvidenceRecord.for_inline_content(
            id=new_id(EvidenceId),
            source_type=EvidenceSourceType.WORKER,
            evidence_type=EvidenceType.REASONING,
            content="Chose bcrypt because it is already used elsewhere",
            work_package_id=draft_work_package.id,
            verified_by_os=True,
        )


def test_system_evidence_is_identified_as_system_evidence(
    system_evidence: EvidenceRecord,
) -> None:
    """Verifies System Evidence is distinguishable from Worker Evidence."""
    assert system_evidence.is_system_evidence


# --------------------------------------------------------------------------
# QA
# --------------------------------------------------------------------------


def _defect(*, is_blocker: bool = False, status: DefectStatus = DefectStatus.OPEN) -> QADefect:
    return QADefect(
        id=new_id(QADefectId),
        title="Login returns 500 for valid credentials",
        severity="CRITICAL",
        priority="P1",
        is_blocker=is_blocker,
        status=status,
    )


def test_passed_qa_report_cannot_carry_unresolved_defects(feature: Feature) -> None:
    """Verifies Design Session 009: zero unresolved defects for a pass."""
    with pytest.raises(ValidationError, match="unresolved defects"):
        QAReport(
            id=new_id(QAReportId),
            feature_id=feature.id,
            status=QAStatus.PASSED,
            defects=(_defect(),),
        )


def test_failed_qa_report_must_record_a_defect(feature: Feature) -> None:
    """Verifies a failure is always explained by a recorded defect."""
    with pytest.raises(ValidationError, match="at least one defect"):
        QAReport(id=new_id(QAReportId), feature_id=feature.id, status=QAStatus.FAILED)


def test_blocked_qa_report_must_record_a_blocker(feature: Feature) -> None:
    """Verifies QA only pauses testing on a recorded blocker."""
    with pytest.raises(ValidationError, match="blocking defect"):
        QAReport(
            id=new_id(QAReportId),
            feature_id=feature.id,
            status=QAStatus.BLOCKED,
            defects=(_defect(is_blocker=False),),
        )


def test_final_pass_must_record_tested_scope_and_results(feature: Feature) -> None:
    """Verifies a QA Final Pass certifies an explicit tested scope."""
    with pytest.raises(ValidationError, match="tested scope"):
        QAReport(
            id=new_id(QAReportId),
            feature_id=feature.id,
            status=QAStatus.PASSED,
            is_final_pass=True,
        )


def test_valid_final_pass_is_identifiable(feature: Feature) -> None:
    """Verifies a valid QA Final Pass is recognisable to the acceptance gate."""
    report = QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.PASSED,
        is_final_pass=True,
        tested_scope=("Email/password login",),
        results=(QATestResult(name="test_login_succeeds", passed=True),),
        defects=(_defect(status=DefectStatus.RESOLVED),),
    )
    assert report.is_valid_final_pass
    assert report.unresolved_defects == ()
    assert report.blocking_defects == ()


def test_failed_report_is_not_a_valid_final_pass(feature: Feature) -> None:
    """Verifies a failing report never satisfies the Final Pass requirement."""
    report = QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.FAILED,
        is_final_pass=True,
        tested_scope=("Email/password login",),
        results=(QATestResult(name="test_login_succeeds", passed=False),),
        defects=(_defect(is_blocker=True),),
    )
    assert not report.is_valid_final_pass
    assert len(report.blocking_defects) == 1


def test_qa_report_rejects_duplicate_defect_identifiers(feature: Feature) -> None:
    """Verifies defects are uniquely identifiable in permanent history."""
    defect = _defect()
    with pytest.raises(ValidationError, match="duplicate defect"):
        QAReport(
            id=new_id(QAReportId),
            feature_id=feature.id,
            status=QAStatus.FAILED,
            defects=(defect, defect),
        )


# --------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------


def _decision(scope: DecisionScope, role: ActorRole, actor: ActorId) -> Decision:
    return Decision(
        id=new_id(DecisionId),
        scope=scope,
        decided_by_role=role,
        decided_by_id=actor,
        problem="Two domains need a shared session contract",
        decision_text="Adopt a single shared session token format",
        reasoning="Avoids duplicate contracts across domains",
    )


@pytest.mark.parametrize(
    ("scope", "role"),
    [
        (DecisionScope.FEATURE, ActorRole.COORDINATOR),
        (DecisionScope.FEATURE, ActorRole.ORCHESTRATOR),
        (DecisionScope.SYSTEM, ActorRole.ORCHESTRATOR),
        (DecisionScope.BUSINESS, ActorRole.BUILDER),
    ],
)
def test_decision_authority_is_respected(scope: DecisionScope, role: ActorRole) -> None:
    """Verifies the escalation chain from Design Sessions 004 and 008."""
    assert _decision(scope, role, new_id(ActorId)).scope is scope


@pytest.mark.parametrize(
    ("scope", "role"),
    [
        (DecisionScope.FEATURE, ActorRole.WORKER),
        (DecisionScope.SYSTEM, ActorRole.COORDINATOR),
        (DecisionScope.BUSINESS, ActorRole.ORCHESTRATOR),
        (DecisionScope.BUSINESS, ActorRole.QA),
    ],
)
def test_decision_beyond_authority_is_rejected(scope: DecisionScope, role: ActorRole) -> None:
    """Verifies a role never records a decision beyond its authority."""
    with pytest.raises(ValidationError, match="cannot record"):
        _decision(scope, role, new_id(ActorId))


def test_review_decision_requires_notes() -> None:
    """Verifies Blueprint 5.2: review outcomes always carry explicit feedback."""
    with pytest.raises(ValidationError):
        ReviewDecision(
            id=new_id(ReviewDecisionId),
            task_revision_id=new_id(TaskRevisionId),
            reviewer_id=new_id(ActorId),
            outcome=ReviewOutcome.CHANGES_REQUESTED,
            notes="",
        )


def test_review_decision_reports_approval(task_revision: TaskRevision) -> None:
    """Verifies the reviewer outcome is deterministically readable."""
    decision = ReviewDecision(
        id=new_id(ReviewDecisionId),
        task_revision_id=task_revision.id,
        reviewer_id=new_id(ActorId),
        outcome=ReviewOutcome.APPROVED,
        notes="Tests cover the new endpoint",
    )
    assert decision.is_approved
