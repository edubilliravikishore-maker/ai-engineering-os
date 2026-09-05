"""Unit tests for the fifteen rules Checkpoint 6 added.

Twelve were computable at Checkpoint 3 and deferred by scope decision; three
needed the Builder rulings of ADR-007. Every distinct failure code is exercised,
because a code is the contract other software branches on and an unexercised one
is a claim rather than a behaviour.

The QA-round tests are the important ones. ADR-007 7.4 exists because a defect
recorded ``OPEN`` in a superseded report stays ``OPEN`` forever, and without a
round the rework loop is unreachable — a Feature that ever failed QA could never
be accepted again. That is asserted directly.
"""

import pytest

from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    Claim,
    DefectStatus,
    EvidenceId,
    EvidenceRecord,
    EvidenceSourceType,
    EvidenceType,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
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
    TaskId,
    TaskRevision,
    TaskRevisionId,
    TaskStatus,
    VerificationGuide,
    WorkPackage,
    WorkPackageId,
    new_id,
)
from ai_engineering_os.domain.qa import TestResult as QATestResult
from ai_engineering_os.domain.task import UNASSIGNED_STATUSES
from ai_engineering_os.rules import (
    RuleCode,
    RuleContext,
    RuleStatus,
)
from ai_engineering_os.rules.acceptance import (
    ImplementationTasksAcceptedRule,
    QAFinalPassRecordedRule,
    QAInScopeZeroDefectsRule,
)
from ai_engineering_os.rules.authority import (
    RequesterIsAssignedWorkerRule,
    ReviewerAssignedRule,
    WorkerIsActiveRule,
)
from ai_engineering_os.rules.evidence import FeatureEvidenceRequiredRule
from ai_engineering_os.rules.planning import (
    FeaturePlanAttachedRule,
    OriginatingPlanActiveRule,
    PlanHasTaskDefinitionsRule,
    PlanIsReadyRule,
)
from ai_engineering_os.rules.submission import (
    ClaimsDefinedRule,
    VerificationGuidePresentRule,
    WorkPackagePresentRule,
)
from ai_engineering_os.rules.verification import (
    QAReportPassedRule,
    ReviewDecisionApprovedRule,
    TestExecutionEvidencePresentRule,
)

# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------


def _feature(*, qa_round: int = 1) -> Feature:
    return Feature(
        id=new_id(FeatureId),
        slug="add-login",
        title="Add login",
        goal="Let a user sign in",
        coordinator_id=new_id(ActorId),
        qa_round=qa_round,
        acceptance_criteria=("A user can sign in",),
    )


def _plan(
    feature: Feature, *, status: PlanStatus = PlanStatus.ACTIVE, tasks: bool = True
) -> FeaturePlan:
    definitions = (
        (
            {
                "key": "sign-in-endpoint",
                "title": "Build the sign-in endpoint",
                "capability": CapabilityType.BACKEND,
            },
        )
        if tasks
        else ()
    )
    return FeaturePlan(
        id=new_id(FeaturePlanId),
        feature_id=feature.id,
        revision_number=1,
        created_by=new_id(ActorId),
        status=status,
        required_capabilities=(CapabilityType.BACKEND,) if tasks else (),
        task_definitions=definitions,  # type: ignore[arg-type]
    )


def _task(
    feature: Feature,
    plan: FeaturePlan,
    *,
    capability: CapabilityType = CapabilityType.BACKEND,
    status: TaskStatus = TaskStatus.SUBMITTED,
    worker_id: ActorId | None = None,
    reviewer_id: ActorId | None = None,
    revision: int = 1,
) -> Task:
    return Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="sign-in-endpoint",
        title="Build the sign-in endpoint",
        capability=capability,
        status=status,
        assigned_worker_id=(
            None if status in UNASSIGNED_STATUSES else worker_id or new_id(ActorId)
        ),
        reviewer_id=reviewer_id,
        active_revision_number=revision,
    )


def _revision(
    task: Task, *, author: ActorId, number: int = 1, work_package_id: WorkPackageId | None = None
) -> TaskRevision:
    return TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=task.id,
        revision_number=number,
        created_by_worker_id=author,
        work_package_id=work_package_id,
    )


def _actor(
    role: ActorRole,
    *,
    active: bool = True,
    capability: CapabilityType | None = CapabilityType.BACKEND,
) -> Actor:
    return Actor(
        id=new_id(ActorId),
        role=role,
        name=f"{role.value.lower()}-1",
        is_active=active,
        capabilities=frozenset({capability}) if capability else frozenset(),
    )


def _evidence(
    kind: EvidenceType,
    *,
    work_package_id: WorkPackageId | None = None,
    qa_report_id: QAReportId | None = None,
) -> EvidenceRecord:
    return EvidenceRecord.for_inline_content(
        id=new_id(EvidenceId),
        source_type=EvidenceSourceType.SYSTEM,
        evidence_type=kind,
        content=f"{kind} payload",
        work_package_id=work_package_id,
        qa_report_id=qa_report_id,
        verified_by_os=True,
    )


def _final_pass(feature: Feature, *, qa_round: int) -> QAReport:
    return QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.PASSED,
        qa_round=qa_round,
        is_final_pass=True,
        tested_scope=("Email/password login",),
        results=(QATestResult(name="login-happy-path", passed=True),),
    )


def _failed_report(feature: Feature, *, qa_round: int, task: Task) -> QAReport:
    return QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.FAILED,
        qa_round=qa_round,
        defects=(
            QADefect(
                id=new_id(QADefectId),
                title="Login returns 500 for valid credentials",
                severity="CRITICAL",
                priority="P1",
                status=DefectStatus.OPEN,
                scope_task_id=task.id,
            ),
        ),
    )


# --------------------------------------------------------------------------
# 7.1 — the definition of an implementation task
# --------------------------------------------------------------------------


def test_a_qa_task_does_not_block_the_start_of_validation() -> None:
    """ADR-007 7.1: requiring it would make validation wait on validation."""
    feature = _feature()
    plan = _plan(feature)
    backend = _task(feature, plan, status=TaskStatus.ACCEPTED, reviewer_id=new_id(ActorId))
    qa = _task(
        feature,
        plan,
        capability=CapabilityType.QA,
        status=TaskStatus.IN_QA,
        reviewer_id=new_id(ActorId),
    )

    result = ImplementationTasksAcceptedRule().evaluate(
        RuleContext(feature=feature, feature_tasks=(backend, qa))
    )

    assert result.status is RuleStatus.PASSED


def test_an_unaccepted_implementation_task_blocks_the_start_of_validation() -> None:
    """A non-QA Task that is not ACCEPTED holds the Feature in IN_PROGRESS."""
    feature = _feature()
    plan = _plan(feature)
    unfinished = _task(feature, plan, status=TaskStatus.IN_PROGRESS)

    result = ImplementationTasksAcceptedRule().evaluate(
        RuleContext(feature=feature, feature_tasks=(unfinished,))
    )

    assert result.code is RuleCode.IMPLEMENTATION_TASK_NOT_ACCEPTED
    assert result.detail("unaccepted_task_ids") == (str(unfinished.id),)


def test_a_feature_with_only_qa_tasks_records_no_implementation_work() -> None:
    """QA Tasks are excluded from the gate, so a Feature of only QA has nothing built."""
    feature = _feature()
    plan = _plan(feature)
    qa = _task(
        feature, plan, capability=CapabilityType.QA, status=TaskStatus.CREATED, worker_id=None
    )

    result = ImplementationTasksAcceptedRule().evaluate(
        RuleContext(
            feature=feature,
            feature_tasks=(
                _task(
                    feature,
                    plan,
                    capability=CapabilityType.QA,
                    status=TaskStatus.ACCEPTED,
                    reviewer_id=new_id(ActorId),
                ),
            ),
        )
    )
    assert result.code is RuleCode.NO_IMPLEMENTATION_TASKS_RECORDED
    assert qa.capability is CapabilityType.QA


# --------------------------------------------------------------------------
# 7.2 — the Feature-level evidence floor
# --------------------------------------------------------------------------


def test_a_feature_carrying_code_tests_and_reasoning_passes() -> None:
    """The three kinds true of every Feature that was genuinely built."""
    feature = _feature()
    work_package_id = new_id(WorkPackageId)
    evidence = tuple(
        _evidence(kind, work_package_id=work_package_id)
        for kind in (EvidenceType.GIT_DIFF, EvidenceType.TEST_OUTPUT, EvidenceType.REASONING)
    )

    result = FeatureEvidenceRequiredRule().evaluate(
        RuleContext(feature=feature, evidence=evidence, qa_reports=())
    )

    assert result.status is RuleStatus.PASSED


def test_missing_reasoning_blocks_acceptance_and_names_what_is_missing() -> None:
    """The Builder's own record is mandatory, and the refusal says which kind."""
    feature = _feature()
    work_package_id = new_id(WorkPackageId)
    evidence = tuple(
        _evidence(kind, work_package_id=work_package_id)
        for kind in (EvidenceType.GIT_DIFF, EvidenceType.TEST_OUTPUT)
    )

    result = FeatureEvidenceRequiredRule().evaluate(
        RuleContext(feature=feature, evidence=evidence, qa_reports=())
    )

    assert result.code is RuleCode.MISSING_FEATURE_EVIDENCE
    assert result.detail("missing_evidence_types") == (str(EvidenceType.REASONING),)


def test_evidence_from_a_superseded_qa_round_does_not_satisfy_acceptance() -> None:
    """Round 1's evidence supported a verdict the Feature has moved past.

    Counting it would let a Feature satisfy the gate on the strength of work
    that was subsequently reworked.
    """
    feature = _feature(qa_round=2)
    old_report = _final_pass(feature, qa_round=1)
    work_package_id = new_id(WorkPackageId)

    evidence = (
        _evidence(EvidenceType.GIT_DIFF, work_package_id=work_package_id),
        _evidence(EvidenceType.TEST_OUTPUT, work_package_id=work_package_id),
        _evidence(EvidenceType.REASONING, qa_report_id=old_report.id),
    )

    result = FeatureEvidenceRequiredRule().evaluate(
        RuleContext(feature=feature, evidence=evidence, qa_reports=(old_report,))
    )

    assert result.code is RuleCode.MISSING_FEATURE_EVIDENCE
    assert result.detail("missing_evidence_types") == (str(EvidenceType.REASONING),)


# --------------------------------------------------------------------------
# 7.3 — reviewer routing
# --------------------------------------------------------------------------


def test_a_task_routed_to_an_eligible_reviewer_passes() -> None:
    feature = _feature()
    plan = _plan(feature)
    reviewer = _actor(ActorRole.REVIEWER)
    worker_id = new_id(ActorId)
    task = _task(
        feature, plan, status=TaskStatus.IN_REVIEW, worker_id=worker_id, reviewer_id=reviewer.id
    )

    result = ReviewerAssignedRule().evaluate(
        RuleContext(
            task=task,
            candidate_reviewers=(reviewer,),
            task_revisions=(_revision(task, author=worker_id),),
        )
    )

    assert result.status is RuleStatus.PASSED


def test_a_task_with_no_reviewer_cannot_enter_review() -> None:
    """The empty-eligible-set outcome: routing recorded nobody, so this refuses."""
    feature = _feature()
    plan = _plan(feature)
    task = _task(feature, plan, status=TaskStatus.SUBMITTED)

    result = ReviewerAssignedRule().evaluate(
        RuleContext(task=task, candidate_reviewers=(), task_revisions=())
    )

    assert result.code is RuleCode.NO_REVIEWER_ROUTED


def test_a_reviewer_who_authored_a_revision_is_refused() -> None:
    """ADR-001 against the Revision history, which is where a previous author hides."""
    feature = _feature()
    plan = _plan(feature)
    reviewer = _actor(ActorRole.REVIEWER)
    task = _task(feature, plan, status=TaskStatus.IN_REVIEW, reviewer_id=reviewer.id)

    result = ReviewerAssignedRule().evaluate(
        RuleContext(
            task=task,
            candidate_reviewers=(reviewer,),
            task_revisions=(_revision(task, author=reviewer.id),),
        )
    )

    assert result.code is RuleCode.REVIEWER_PERFORMED_THE_WORK


def test_a_reviewer_without_the_task_capability_is_refused() -> None:
    feature = _feature()
    plan = _plan(feature)
    reviewer = _actor(ActorRole.REVIEWER, capability=CapabilityType.FRONTEND)
    task = _task(feature, plan, status=TaskStatus.IN_REVIEW, reviewer_id=reviewer.id)

    result = ReviewerAssignedRule().evaluate(
        RuleContext(task=task, candidate_reviewers=(reviewer,), task_revisions=())
    )

    assert result.code is RuleCode.REVIEWER_CAPABILITY_MISMATCH


def test_a_reviewer_the_os_may_not_route_to_is_refused() -> None:
    """A Reviewer recorded on the Task but absent from the routable set."""
    feature = _feature()
    plan = _plan(feature)
    task = _task(feature, plan, status=TaskStatus.IN_REVIEW, reviewer_id=new_id(ActorId))

    result = ReviewerAssignedRule().evaluate(
        RuleContext(task=task, candidate_reviewers=(), task_revisions=())
    )

    assert result.code is RuleCode.REVIEWER_NOT_ELIGIBLE


# --------------------------------------------------------------------------
# 7.4 — QA rounds
# --------------------------------------------------------------------------


def test_a_feature_that_failed_qa_once_can_be_accepted_after_rework() -> None:
    """The rework loop is reachable. This is what ADR-007 7.4 exists for.

    Round 1 recorded an OPEN defect, and that record is permanent. Round 2
    passed. Without the round filter the Feature would be blocked forever by a
    report describing work that no longer exists.
    """
    feature = _feature(qa_round=2)
    plan = _plan(feature)
    task = _task(feature, plan, status=TaskStatus.ACCEPTED, reviewer_id=new_id(ActorId))
    reports = (
        _failed_report(feature, qa_round=1, task=task),
        _final_pass(feature, qa_round=2),
    )
    context = RuleContext(
        feature=feature, feature_tasks=(task,), referenced_tasks=(), qa_reports=reports
    )

    assert QAFinalPassRecordedRule().evaluate(context).status is RuleStatus.PASSED
    assert QAInScopeZeroDefectsRule().evaluate(context).status is RuleStatus.PASSED


def test_an_open_defect_in_the_current_round_still_blocks_acceptance() -> None:
    """The filter narrows by round; it does not weaken the rule."""
    feature = _feature(qa_round=2)
    plan = _plan(feature)
    task = _task(feature, plan, status=TaskStatus.ACCEPTED, reviewer_id=new_id(ActorId))
    reports = (
        _failed_report(feature, qa_round=2, task=task),
        _final_pass(feature, qa_round=2),
    )

    result = QAInScopeZeroDefectsRule().evaluate(
        RuleContext(feature=feature, feature_tasks=(task,), referenced_tasks=(), qa_reports=reports)
    )

    assert result.code is RuleCode.UNRESOLVED_IN_SCOPE_DEFECT
    assert result.detail("qa_round") == ("2",)


def test_a_final_pass_from_an_earlier_round_does_not_certify_the_feature() -> None:
    """It certified work that has since changed; it stays on record regardless."""
    feature = _feature(qa_round=2)

    result = QAFinalPassRecordedRule().evaluate(
        RuleContext(feature=feature, qa_reports=(_final_pass(feature, qa_round=1),))
    )

    assert result.code is RuleCode.MISSING_QA_FINAL_PASS


# --------------------------------------------------------------------------
# The twelve rules deferred by scope at Checkpoint 3
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        (_actor(ActorRole.WORKER), None),
        (_actor(ActorRole.WORKER, active=False), RuleCode.WORKER_INACTIVE),
        (_actor(ActorRole.REVIEWER), RuleCode.ACTOR_IS_NOT_A_WORKER),
    ],
    ids=["active-worker", "inactive-worker", "not-a-worker"],
)
def test_worker_is_active(actor: Actor, expected: RuleCode | None) -> None:
    result = WorkerIsActiveRule().evaluate(RuleContext(candidate_worker=actor))
    assert result.code is expected


def test_only_the_assigned_worker_may_start_a_task() -> None:
    feature = _feature()
    plan = _plan(feature)
    worker = _actor(ActorRole.WORKER)
    task = _task(feature, plan, status=TaskStatus.ASSIGNED, worker_id=worker.id, revision=0)

    assert (
        RequesterIsAssignedWorkerRule()
        .evaluate(RuleContext(requesting_actor=worker, task=task))
        .status
        is RuleStatus.PASSED
    )

    stranger = _actor(ActorRole.WORKER)
    assert (
        RequesterIsAssignedWorkerRule()
        .evaluate(RuleContext(requesting_actor=stranger, task=task))
        .code
        is RuleCode.REQUESTER_IS_NOT_THE_ASSIGNED_WORKER
    )


def test_a_feature_with_no_live_plan_cannot_be_planned() -> None:
    feature = _feature()
    superseded = _plan(feature, status=PlanStatus.SUPERSEDED)

    result = FeaturePlanAttachedRule().evaluate(
        RuleContext(feature=feature, feature_plans=(superseded,))
    )

    assert result.code is RuleCode.NO_FEATURE_PLAN_ATTACHED


def test_a_plan_defining_no_task_cannot_plan_a_feature() -> None:
    feature = _feature()
    empty = _plan(feature, status=PlanStatus.DRAFT, tasks=False)

    result = PlanHasTaskDefinitionsRule().evaluate(
        RuleContext(feature=feature, feature_plans=(empty,))
    )

    assert result.code is RuleCode.PLAN_DEFINES_NO_TASKS


def test_a_draft_plan_is_not_ready_to_execute() -> None:
    feature = _feature()
    draft = _plan(feature, status=PlanStatus.DRAFT)

    result = PlanIsReadyRule().evaluate(RuleContext(feature=feature, feature_plans=(draft,)))

    assert result.code is RuleCode.PLAN_NOT_READY


def test_a_task_whose_plan_is_not_active_may_not_become_ready() -> None:
    """ADR-003 3.12: existence confers no execution authority."""
    feature = _feature()
    plan = _plan(feature, status=PlanStatus.READY)
    task = _task(feature, plan, status=TaskStatus.CREATED, worker_id=None, revision=0)

    result = OriginatingPlanActiveRule().evaluate(RuleContext(task=task, feature_plans=(plan,)))

    assert result.code is RuleCode.ORIGINATING_PLAN_NOT_ACTIVE


def test_a_task_whose_plan_was_not_supplied_fails_closed() -> None:
    """The OS does not assume a plan it cannot see is active."""
    feature = _feature()
    plan = _plan(feature)
    task = _task(feature, plan, status=TaskStatus.CREATED, worker_id=None, revision=0)

    result = OriginatingPlanActiveRule().evaluate(RuleContext(task=task, feature_plans=()))

    assert result.code is RuleCode.ORIGINATING_PLAN_NOT_SUPPLIED


def test_the_submission_gate_reports_each_omission_separately() -> None:
    """Three different omissions with three different remedies."""
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(feature, plan, worker_id=worker_id)
    package = WorkPackage(
        id=new_id(WorkPackageId),
        task_revision_id=new_id(TaskRevisionId),
        summary="Implemented the sign-in endpoint",
    )
    revision = _revision(task, author=worker_id, work_package_id=package.id)
    bound = package.model_copy(update={"task_revision_id": revision.id})

    context = RuleContext(task=task, task_revisions=(revision,), work_packages=(bound,))

    assert WorkPackagePresentRule().evaluate(context).status is RuleStatus.PASSED
    assert ClaimsDefinedRule().evaluate(context).code is RuleCode.NO_CLAIMS_DECLARED
    assert VerificationGuidePresentRule().evaluate(context).code is RuleCode.NO_VERIFICATION_GUIDE


def test_a_task_with_no_work_package_cannot_be_submitted() -> None:
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(feature, plan, worker_id=worker_id)

    result = WorkPackagePresentRule().evaluate(
        RuleContext(
            task=task, task_revisions=(_revision(task, author=worker_id),), work_packages=()
        )
    )

    assert result.code is RuleCode.NO_WORK_PACKAGE_SUBMITTED


def test_a_complete_work_package_satisfies_the_submission_gate(
    claim: Claim, verification_guide: VerificationGuide
) -> None:
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(feature, plan, worker_id=worker_id)
    revision = _revision(task, author=worker_id)
    package = WorkPackage(
        id=new_id(WorkPackageId),
        task_revision_id=revision.id,
        summary="Implemented the sign-in endpoint",
        claims=(claim,),
        verification_guide=verification_guide,
    )
    context = RuleContext(task=task, task_revisions=(revision,), work_packages=(package,))

    assert ClaimsDefinedRule().evaluate(context).status is RuleStatus.PASSED
    assert VerificationGuidePresentRule().evaluate(context).status is RuleStatus.PASSED


def test_a_revision_with_changes_requested_does_not_reach_qa() -> None:
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(
        feature, plan, status=TaskStatus.IN_REVIEW, worker_id=worker_id, reviewer_id=new_id(ActorId)
    )
    revision = _revision(task, author=worker_id)
    decision = ReviewDecision(
        id=new_id(ReviewDecisionId),
        task_revision_id=revision.id,
        reviewer_id=new_id(ActorId),
        outcome=ReviewOutcome.CHANGES_REQUESTED,
        notes="The endpoint does not validate the password length",
    )

    result = ReviewDecisionApprovedRule().evaluate(
        RuleContext(task=task, task_revisions=(revision,), review_decisions=(decision,))
    )

    assert result.code is RuleCode.REVIEW_CHANGES_REQUESTED


def test_a_revision_with_no_review_decision_does_not_reach_qa() -> None:
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(
        feature, plan, status=TaskStatus.IN_REVIEW, worker_id=worker_id, reviewer_id=new_id(ActorId)
    )

    result = ReviewDecisionApprovedRule().evaluate(
        RuleContext(
            task=task,
            task_revisions=(_revision(task, author=worker_id),),
            review_decisions=(),
        )
    )

    assert result.code is RuleCode.NO_REVIEW_DECISION_RECORDED


def test_a_task_is_accepted_only_on_a_passed_qa_report() -> None:
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(
        feature, plan, status=TaskStatus.IN_QA, worker_id=worker_id, reviewer_id=new_id(ActorId)
    )
    revision = _revision(task, author=worker_id)
    blocked = QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.BLOCKED,
        task_revision_id=revision.id,
        defects=(
            QADefect(
                id=new_id(QADefectId),
                title="Test environment unavailable",
                severity="HIGH",
                priority="P1",
                is_blocker=True,
            ),
        ),
    )

    result = QAReportPassedRule().evaluate(
        RuleContext(task=task, task_revisions=(revision,), qa_reports=(blocked,))
    )

    assert result.code is RuleCode.QA_REPORT_DID_NOT_PASS
    assert result.detail("qa_status") == (str(QAStatus.BLOCKED),)


def test_a_passing_qa_report_must_evidence_an_actual_test_run() -> None:
    """A report claiming a pass with no test output is an assertion, not a verification."""
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(
        feature, plan, status=TaskStatus.IN_QA, worker_id=worker_id, reviewer_id=new_id(ActorId)
    )
    revision = _revision(task, author=worker_id)
    report = QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.PASSED,
        task_revision_id=revision.id,
        results=(QATestResult(name="login-happy-path", passed=True),),
    )
    context = RuleContext(task=task, task_revisions=(revision,), qa_reports=(report,), evidence=())

    assert (
        TestExecutionEvidencePresentRule().evaluate(context).code
        is RuleCode.NO_TEST_EXECUTION_EVIDENCE
    )

    with_output = RuleContext(
        task=task,
        task_revisions=(revision,),
        qa_reports=(report,),
        evidence=(_evidence(EvidenceType.TEST_OUTPUT, qa_report_id=report.id),),
    )
    assert TestExecutionEvidencePresentRule().evaluate(with_output).status is RuleStatus.PASSED


def test_a_qa_report_recording_no_test_result_is_refused() -> None:
    feature = _feature()
    plan = _plan(feature)
    worker_id = new_id(ActorId)
    task = _task(
        feature, plan, status=TaskStatus.IN_QA, worker_id=worker_id, reviewer_id=new_id(ActorId)
    )
    revision = _revision(task, author=worker_id)
    report = QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.PASSED,
        task_revision_id=revision.id,
    )

    result = TestExecutionEvidencePresentRule().evaluate(
        RuleContext(task=task, task_revisions=(revision,), qa_reports=(report,), evidence=())
    )

    assert result.code is RuleCode.NO_TEST_RESULTS_RECORDED
