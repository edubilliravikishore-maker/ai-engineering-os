"""Unit tests for the six Checkpoint 3 rules (ADR-004 4.9, 4.10).

Every distinct failure code of every rule is exercised, together with the
structured details a rejection must carry. The full ADR-003 3.11 defect-scope
matrix has its own section.
"""

import pytest

from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    DefectStatus,
    EvidenceId,
    EvidenceRecord,
    EvidenceSourceType,
    EvidenceType,
    Feature,
    FeatureId,
    FeaturePlan,
    QADefect,
    QADefectId,
    QAReport,
    QAReportId,
    QAStatus,
    Task,
    TaskId,
    TaskStatus,
    TransitionCondition,
    WorkPackageId,
    new_id,
)
from ai_engineering_os.domain.qa import TestResult as QATestResult
from ai_engineering_os.rules import (
    MANDATORY_SYSTEM_EVIDENCE,
    AllTasksAcceptedRule,
    DependenciesAcceptedRule,
    QAFinalPassRecordedRule,
    QAInScopeZeroDefectsRule,
    RuleCode,
    RuleContext,
    RuleId,
    RuleStage,
    RuleStatus,
    SystemEvidenceRequiredRule,
    WorkerCapabilityMatchesRule,
)

# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------


def _task(
    *,
    feature: Feature,
    plan: FeaturePlan,
    key: str = "auth-api",
    capability: CapabilityType = CapabilityType.BACKEND,
    status: TaskStatus = TaskStatus.CREATED,
    dependencies: tuple[TaskId, ...] = (),
    worker_id: ActorId | None = None,
) -> Task:
    return Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key=key,
        title="Implement Auth API",
        capability=capability,
        status=status,
        dependencies=dependencies,
        assigned_worker_id=worker_id,
        active_revision_number=1 if status is TaskStatus.ACCEPTED else 0,
    )


def _accepted_task(*, feature: Feature, plan: FeaturePlan, worker_id: ActorId) -> Task:
    return _task(feature=feature, plan=plan, status=TaskStatus.ACCEPTED, worker_id=worker_id)


def _system_evidence(*, kinds: tuple[EvidenceType, ...]) -> tuple[EvidenceRecord, ...]:
    work_package_id = new_id(WorkPackageId)
    return tuple(
        EvidenceRecord.for_inline_content(
            id=new_id(EvidenceId),
            source_type=EvidenceSourceType.SYSTEM,
            evidence_type=kind,
            content=f"{kind} payload",
            work_package_id=work_package_id,
            verified_by_os=True,
        )
        for kind in kinds
    )


def _defect(
    *,
    status: DefectStatus = DefectStatus.OPEN,
    scope_task_id: TaskId | None = None,
    scope_feature_id: FeatureId | None = None,
    title: str = "Login returns 500 for valid credentials",
) -> QADefect:
    return QADefect(
        id=new_id(QADefectId),
        title=title,
        severity="CRITICAL",
        priority="P1",
        status=status,
        scope_task_id=scope_task_id,
        scope_feature_id=scope_feature_id,
    )


def _final_pass(feature: Feature) -> QAReport:
    return QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.PASSED,
        is_final_pass=True,
        tested_scope=("Email/password login",),
        results=(QATestResult(name="login-happy-path", passed=True),),
    )


def _failed_report(feature: Feature, *defects: QADefect) -> QAReport:
    return QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.FAILED,
        defects=defects,
    )


# --------------------------------------------------------------------------
# worker_capability_matches
# --------------------------------------------------------------------------


def test_capability_rule_declares_its_contract() -> None:
    """Verifies the rule's machine contract is stable and explicit."""
    rule = WorkerCapabilityMatchesRule()
    assert rule.rule_id is RuleId.WORKER_CAPABILITY_MATCHES
    assert rule.condition is TransitionCondition.WORKER_CAPABILITY_MATCHES
    assert rule.stage is RuleStage.ACTOR_AUTHORITY
    assert rule.requires == frozenset()


def test_a_matching_worker_passes(backend_worker: Actor, task: Task) -> None:
    """Verifies a Worker declaring the Task's capability may be assigned."""
    result = WorkerCapabilityMatchesRule().evaluate(
        RuleContext(candidate_worker=backend_worker, task=task)
    )
    assert result.status is RuleStatus.PASSED
    assert result.code is None


def test_a_mismatched_worker_fails(task: Task) -> None:
    """Verifies the Blueprint 5.2 capability requirement is enforced."""
    frontend_worker = Actor(
        id=new_id(ActorId),
        role=ActorRole.WORKER,
        name="frontend-worker-1",
        capabilities=frozenset({CapabilityType.FRONTEND}),
    )
    result = WorkerCapabilityMatchesRule().evaluate(
        RuleContext(candidate_worker=frontend_worker, task=task)
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.WORKER_CAPABILITY_MISMATCH
    assert result.detail("required_capability") == ("BACKEND",)
    assert result.detail("worker_capabilities") == ("FRONTEND",)
    assert result.detail("task_id") == (str(task.id),)


def test_capability_is_read_from_the_actor_not_the_request(task: Task) -> None:
    """Verifies authority never follows from the request itself."""
    multi_capability = Actor(
        id=new_id(ActorId),
        role=ActorRole.WORKER,
        name="full-stack-worker",
        capabilities=frozenset({CapabilityType.BACKEND, CapabilityType.FRONTEND}),
    )
    result = WorkerCapabilityMatchesRule().evaluate(
        RuleContext(candidate_worker=multi_capability, task=task)
    )
    assert result.status is RuleStatus.PASSED


# --------------------------------------------------------------------------
# dependencies_accepted
# --------------------------------------------------------------------------


def test_a_task_with_no_dependencies_passes(task: Task) -> None:
    """Verifies CREATED -> READY is satisfied vacuously with no prerequisites."""
    result = DependenciesAcceptedRule().evaluate(
        RuleContext(task=task, feature_tasks=(task,), referenced_tasks=())
    )
    assert result.status is RuleStatus.PASSED


def test_accepted_dependencies_pass(
    feature: Feature, feature_plan: FeaturePlan, worker_id: ActorId
) -> None:
    """Verifies a Task whose prerequisites are all ACCEPTED may become READY."""
    prerequisite = _accepted_task(feature=feature, plan=feature_plan, worker_id=worker_id)
    dependent = _task(feature=feature, plan=feature_plan, dependencies=(prerequisite.id,))
    result = DependenciesAcceptedRule().evaluate(
        RuleContext(task=dependent, feature_tasks=(prerequisite, dependent), referenced_tasks=())
    )
    assert result.status is RuleStatus.PASSED


def test_an_unaccepted_dependency_fails(feature: Feature, feature_plan: FeaturePlan) -> None:
    """Verifies work never starts on top of unfinished prerequisites."""
    prerequisite = _task(feature=feature, plan=feature_plan, status=TaskStatus.CREATED)
    dependent = _task(feature=feature, plan=feature_plan, dependencies=(prerequisite.id,))
    result = DependenciesAcceptedRule().evaluate(
        RuleContext(task=dependent, feature_tasks=(dependent,), referenced_tasks=(prerequisite,))
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.DEPENDENCY_NOT_ACCEPTED
    assert result.detail("unaccepted_dependencies") == (str(prerequisite.id),)
    assert result.detail("unaccepted_dependency_statuses") == ("CREATED",)


def test_an_unresolvable_dependency_fails_closed(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies an unknown dependency fact never yields a silent pass."""
    missing_id = new_id(TaskId)
    dependent = _task(feature=feature, plan=feature_plan, dependencies=(missing_id,))
    result = DependenciesAcceptedRule().evaluate(
        RuleContext(task=dependent, feature_tasks=(dependent,), referenced_tasks=())
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.DEPENDENCY_FACTS_MISSING
    assert result.detail("unresolved_dependencies") == (str(missing_id),)


def test_unresolvable_facts_take_precedence_over_an_unaccepted_dependency(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies the OS reports what it cannot determine before what it can."""
    known = _task(feature=feature, plan=feature_plan, status=TaskStatus.CREATED)
    missing_id = new_id(TaskId)
    dependent = _task(feature=feature, plan=feature_plan, dependencies=(known.id, missing_id))
    result = DependenciesAcceptedRule().evaluate(
        RuleContext(task=dependent, feature_tasks=(dependent, known), referenced_tasks=())
    )
    assert result.code is RuleCode.DEPENDENCY_FACTS_MISSING


# --------------------------------------------------------------------------
# system_evidence_required
# --------------------------------------------------------------------------


def test_backend_evidence_standard_matches_design_session_005() -> None:
    """Verifies the mandatory set is exactly the Design Session 005 Backend list."""
    assert MANDATORY_SYSTEM_EVIDENCE[CapabilityType.BACKEND] == (
        EvidenceType.GIT_DIFF,
        EvidenceType.TEST_OUTPUT,
        EvidenceType.API_RESPONSE,
    )


def test_db_verification_is_not_mandatory() -> None:
    """Verifies ADR-004 4.9 keeps DB_VERIFICATION out of the deterministic set."""
    for required in MANDATORY_SYSTEM_EVIDENCE.values():
        assert EvidenceType.DB_VERIFICATION not in required


def test_complete_backend_evidence_passes(task: Task) -> None:
    """Verifies a fully evidenced backend submission satisfies the Stage 1 gate."""
    evidence = _system_evidence(
        kinds=(EvidenceType.GIT_DIFF, EvidenceType.TEST_OUTPUT, EvidenceType.API_RESPONSE)
    )
    result = SystemEvidenceRequiredRule().evaluate(RuleContext(task=task, evidence=evidence))
    assert result.status is RuleStatus.PASSED


def test_missing_backend_evidence_fails_and_names_what_is_missing(task: Task) -> None:
    """Verifies the rejection carries the required and the missing evidence."""
    evidence = _system_evidence(kinds=(EvidenceType.GIT_DIFF,))
    result = SystemEvidenceRequiredRule().evaluate(RuleContext(task=task, evidence=evidence))
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.MISSING_SYSTEM_EVIDENCE
    assert result.detail("required_evidence") == ("GIT_DIFF", "TEST_OUTPUT", "API_RESPONSE")
    assert result.detail("missing_evidence") == ("TEST_OUTPUT", "API_RESPONSE")


def test_worker_evidence_does_not_discharge_a_system_requirement(task: Task) -> None:
    """Verifies only independently generated Evidence satisfies the minimum."""
    worker_evidence = tuple(
        EvidenceRecord.for_inline_content(
            id=new_id(EvidenceId),
            source_type=EvidenceSourceType.WORKER,
            evidence_type=kind,
            content=f"{kind} explanation",
            work_package_id=new_id(WorkPackageId),
        )
        for kind in (EvidenceType.GIT_DIFF, EvidenceType.TEST_OUTPUT, EvidenceType.API_RESPONSE)
    )
    result = SystemEvidenceRequiredRule().evaluate(RuleContext(task=task, evidence=worker_evidence))
    assert result.code is RuleCode.MISSING_SYSTEM_EVIDENCE
    assert result.detail("missing_evidence") == ("GIT_DIFF", "TEST_OUTPUT", "API_RESPONSE")


@pytest.mark.parametrize("capability", [CapabilityType.FRONTEND, CapabilityType.QA])
def test_an_undefined_standard_fails_closed(
    feature: Feature, feature_plan: FeaturePlan, capability: CapabilityType
) -> None:
    """Verifies ADR-004 4.9: an unruled standard never means "no evidence required"."""
    task = _task(feature=feature, plan=feature_plan, capability=capability)
    evidence = _system_evidence(
        kinds=(EvidenceType.GIT_DIFF, EvidenceType.TEST_OUTPUT, EvidenceType.API_RESPONSE)
    )
    result = SystemEvidenceRequiredRule().evaluate(RuleContext(task=task, evidence=evidence))
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.EVIDENCE_STANDARD_UNDEFINED
    assert result.detail("capability") == (capability,)


def test_the_undefined_standard_code_is_distinct_from_missing_evidence(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies a rejection never falsely blames the Worker for an OS gap."""
    frontend_task = _task(feature=feature, plan=feature_plan, capability=CapabilityType.FRONTEND)
    result = SystemEvidenceRequiredRule().evaluate(RuleContext(task=frontend_task, evidence=()))
    assert result.code is not RuleCode.MISSING_SYSTEM_EVIDENCE
    assert result.code is RuleCode.EVIDENCE_STANDARD_UNDEFINED


def test_evidence_is_keyed_off_capability_not_claim_type(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies ADR-003 3.7: the standard follows Task.capability alone.

    Two Tasks carrying identical evidence but different capabilities must reach
    different verdicts, which is only possible if capability is the key.
    """
    evidence = _system_evidence(
        kinds=(EvidenceType.GIT_DIFF, EvidenceType.TEST_OUTPUT, EvidenceType.API_RESPONSE)
    )
    backend = _task(feature=feature, plan=feature_plan, capability=CapabilityType.BACKEND)
    frontend = _task(feature=feature, plan=feature_plan, capability=CapabilityType.FRONTEND)
    rule = SystemEvidenceRequiredRule()
    assert rule.evaluate(RuleContext(task=backend, evidence=evidence)).status is RuleStatus.PASSED
    assert rule.evaluate(RuleContext(task=frontend, evidence=evidence)).status is RuleStatus.FAILED


# --------------------------------------------------------------------------
# all_tasks_accepted
# --------------------------------------------------------------------------


def test_all_accepted_tasks_pass(
    feature: Feature, feature_plan: FeaturePlan, worker_id: ActorId
) -> None:
    """Verifies a Feature whose Tasks are all ACCEPTED clears this gate."""
    tasks = (
        _accepted_task(feature=feature, plan=feature_plan, worker_id=worker_id),
        _accepted_task(feature=feature, plan=feature_plan, worker_id=worker_id),
    )
    result = AllTasksAcceptedRule().evaluate(RuleContext(feature=feature, feature_tasks=tasks))
    assert result.status is RuleStatus.PASSED


def test_an_unaccepted_task_blocks_feature_acceptance(
    feature: Feature, feature_plan: FeaturePlan, worker_id: ActorId
) -> None:
    """Verifies unfinished work is named in the rejection."""
    accepted = _accepted_task(feature=feature, plan=feature_plan, worker_id=worker_id)
    open_task = _task(feature=feature, plan=feature_plan, status=TaskStatus.CREATED)
    result = AllTasksAcceptedRule().evaluate(
        RuleContext(feature=feature, feature_tasks=(accepted, open_task))
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.TASK_NOT_ACCEPTED
    assert result.detail("unaccepted_task_ids") == (str(open_task.id),)
    assert result.detail("unaccepted_task_statuses") == ("CREATED",)


def test_a_feature_with_no_tasks_fails(feature: Feature) -> None:
    """Verifies there must be delivered work before there is anything to accept."""
    result = AllTasksAcceptedRule().evaluate(RuleContext(feature=feature, feature_tasks=()))
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.NO_TASKS_RECORDED


def test_a_task_of_another_feature_is_not_counted(
    feature: Feature, feature_plan: FeaturePlan, coordinator_id: ActorId
) -> None:
    """Verifies acceptance considers only the Feature's own Tasks."""
    other_feature = Feature(
        id=new_id(FeatureId),
        slug="other-feature",
        title="Other Feature",
        goal="Unrelated capability",
        coordinator_id=coordinator_id,
    )
    foreign = _task(feature=other_feature, plan=feature_plan, status=TaskStatus.CREATED)
    result = AllTasksAcceptedRule().evaluate(RuleContext(feature=feature, feature_tasks=(foreign,)))
    assert result.code is RuleCode.NO_TASKS_RECORDED


# --------------------------------------------------------------------------
# qa_final_pass_recorded
# --------------------------------------------------------------------------


def test_a_valid_final_pass_passes(feature: Feature) -> None:
    """Verifies an authoritative QA Final Pass satisfies the condition."""
    result = QAFinalPassRecordedRule().evaluate(
        RuleContext(feature=feature, qa_reports=(_final_pass(feature),))
    )
    assert result.status is RuleStatus.PASSED


def test_no_final_pass_fails(feature: Feature) -> None:
    """Verifies acceptance requires QA to have certified the Feature."""
    result = QAFinalPassRecordedRule().evaluate(
        RuleContext(feature=feature, qa_reports=(_failed_report(feature, _defect()),))
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.MISSING_QA_FINAL_PASS


def test_an_invalid_final_pass_fails(feature: Feature) -> None:
    """Verifies a report claiming to be a Final Pass is not accepted as one."""
    blocked_final_pass = QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.BLOCKED,
        is_final_pass=True,
        tested_scope=("Email/password login",),
        results=(QATestResult(name="login-happy-path", passed=False),),
        defects=(
            QADefect(
                id=new_id(QADefectId),
                title="Environment unavailable",
                severity="CRITICAL",
                priority="P1",
                is_blocker=True,
            ),
        ),
    )
    result = QAFinalPassRecordedRule().evaluate(
        RuleContext(feature=feature, qa_reports=(blocked_final_pass,))
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.INVALID_QA_FINAL_PASS
    assert result.detail("qa_report_ids") == (str(blocked_final_pass.id),)
    assert result.detail("qa_report_statuses") == ("BLOCKED",)


def test_a_final_pass_for_another_feature_does_not_count(
    feature: Feature, coordinator_id: ActorId
) -> None:
    """Verifies a Final Pass certifies exactly one Feature."""
    other_feature = Feature(
        id=new_id(FeatureId),
        slug="other-feature",
        title="Other Feature",
        goal="Unrelated capability",
        coordinator_id=coordinator_id,
    )
    result = QAFinalPassRecordedRule().evaluate(
        RuleContext(feature=feature, qa_reports=(_final_pass(other_feature),))
    )
    assert result.code is RuleCode.MISSING_QA_FINAL_PASS


def test_qa_final_pass_is_the_declared_prerequisite_provider() -> None:
    """Verifies the prerequisite relationship of ADR-004 4.10 is declared, not inferred."""
    assert QAInScopeZeroDefectsRule.requires == frozenset({RuleId.QA_FINAL_PASS_RECORDED})
    assert QAFinalPassRecordedRule.requires == frozenset()


# --------------------------------------------------------------------------
# qa_in_scope_zero_defects — the ADR-003 3.11 scope matrix
# --------------------------------------------------------------------------


def _scope_context(
    *,
    feature: Feature,
    reports: tuple[QAReport, ...],
    feature_tasks: tuple[Task, ...] = (),
    referenced_tasks: tuple[Task, ...] = (),
) -> RuleContext:
    return RuleContext(
        feature=feature,
        qa_reports=reports,
        feature_tasks=feature_tasks,
        referenced_tasks=referenced_tasks,
    )


def test_no_defects_passes(feature: Feature) -> None:
    """Verifies a clean Feature carries no unresolved in-scope defect."""
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(feature=feature, reports=(_final_pass(feature),))
    )
    assert result.status is RuleStatus.PASSED


def test_defect_against_a_task_of_this_feature_blocks(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Matrix: Defect -> Task -> current Feature blocks acceptance."""
    task = _task(feature=feature, plan=feature_plan)
    report = _failed_report(feature, _defect(scope_task_id=task.id))
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(feature=feature, reports=(report,), feature_tasks=(task,))
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.UNRESOLVED_IN_SCOPE_DEFECT
    assert result.detail("in_scope_defect_ids") == (str(report.defects[0].id),)
    assert result.detail("in_scope_defect_titles") == (report.defects[0].title,)


def test_defect_against_this_feature_directly_blocks(feature: Feature) -> None:
    """Matrix: Defect -> current Feature blocks acceptance."""
    report = _failed_report(feature, _defect(scope_feature_id=feature.id))
    result = QAInScopeZeroDefectsRule().evaluate(_scope_context(feature=feature, reports=(report,)))
    assert result.code is RuleCode.UNRESOLVED_IN_SCOPE_DEFECT


def test_defect_against_a_task_of_another_feature_does_not_block(
    feature: Feature, feature_plan: FeaturePlan, coordinator_id: ActorId
) -> None:
    """Matrix: Defect -> Task -> another Feature does not block this Feature."""
    other_feature = Feature(
        id=new_id(FeatureId),
        slug="other-feature",
        title="Other Feature",
        goal="Unrelated capability",
        coordinator_id=coordinator_id,
    )
    foreign_task = _task(feature=other_feature, plan=feature_plan)
    report = _failed_report(feature, _defect(scope_task_id=foreign_task.id))
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(feature=feature, reports=(report,), referenced_tasks=(foreign_task,))
    )
    assert result.status is RuleStatus.PASSED


def test_defect_against_another_feature_directly_does_not_block(feature: Feature) -> None:
    """Verifies ADR-003 3.11 as amended: a different Feature is out of scope, not unresolved."""
    other_feature_id = new_id(FeatureId)
    assert other_feature_id != feature.id
    report = _failed_report(feature, _defect(scope_feature_id=other_feature_id))
    result = QAInScopeZeroDefectsRule().evaluate(_scope_context(feature=feature, reports=(report,)))
    assert result.status is RuleStatus.PASSED


def test_a_defect_with_no_association_is_scope_unresolved(feature: Feature) -> None:
    """Matrix: a defect with no association leaves scope unresolved."""
    report = _failed_report(feature, _defect())
    result = QAInScopeZeroDefectsRule().evaluate(_scope_context(feature=feature, reports=(report,)))
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.DEFECT_SCOPE_UNRESOLVED
    assert result.detail("scope_unresolved_defect_ids") == (str(report.defects[0].id),)
    assert result.detail("scope_unresolved_defect_titles") == (report.defects[0].title,)


def test_a_dangling_task_association_is_scope_unresolved(feature: Feature) -> None:
    """Matrix: an association resolving to no supplied Task leaves scope unresolved."""
    report = _failed_report(feature, _defect(scope_task_id=new_id(TaskId)))
    result = QAInScopeZeroDefectsRule().evaluate(_scope_context(feature=feature, reports=(report,)))
    assert result.code is RuleCode.DEFECT_SCOPE_UNRESOLVED


def test_a_resolved_defect_does_not_block(feature: Feature, feature_plan: FeaturePlan) -> None:
    """Matrix: a resolved defect does not block acceptance."""
    task = _task(feature=feature, plan=feature_plan)
    report = _failed_report(feature, _defect(status=DefectStatus.RESOLVED, scope_task_id=task.id))
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(feature=feature, reports=(report,), feature_tasks=(task,))
    )
    assert result.status is RuleStatus.PASSED


def test_a_resolved_defect_with_no_association_does_not_block(feature: Feature) -> None:
    """Verifies scope is only resolved for defects that still block."""
    report = _failed_report(feature, _defect(status=DefectStatus.RESOLVED))
    result = QAInScopeZeroDefectsRule().evaluate(_scope_context(feature=feature, reports=(report,)))
    assert result.status is RuleStatus.PASSED


def test_scope_is_never_read_from_a_declared_boolean() -> None:
    """Verifies ADR-003 3.11: the model exposes no in-scope flag to read."""
    assert "in_scope" not in QADefect.model_fields
    assert not any(field.startswith("in_scope") for field in QADefect.model_fields)


def test_scope_unresolved_takes_precedence_but_both_sets_are_reported(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies an unresolvable scope is reported first and nothing is hidden."""
    task = _task(feature=feature, plan=feature_plan)
    report = _failed_report(
        feature,
        _defect(scope_task_id=task.id, title="In-scope defect"),
        _defect(title="Unassociated defect"),
    )
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(feature=feature, reports=(report,), feature_tasks=(task,))
    )
    assert result.code is RuleCode.DEFECT_SCOPE_UNRESOLVED
    assert result.detail("scope_unresolved_defect_titles") == ("Unassociated defect",)
    assert result.detail("in_scope_defect_titles") == ("In-scope defect",)


def test_the_rule_takes_no_view_on_how_many_reports_it_receives(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies the rule evaluates supplied facts and never judges their cardinality.

    Repeat QA is normal: a report exists per Task Revision, and the Blueprint 5.1
    ``IN_VALIDATION -> IN_PROGRESS`` rework loop produces more of them. A rule
    that rejected a Feature merely because several reports were supplied would be
    inventing QA workflow semantics it does not own (ADR-004 4.15).
    """
    task = _task(feature=feature, plan=feature_plan)
    resolved_defect = _defect(status=DefectStatus.RESOLVED, scope_task_id=task.id)
    reports = (_failed_report(feature, resolved_defect), _final_pass(feature))
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(feature=feature, reports=reports, feature_tasks=(task,))
    )
    assert result.status is RuleStatus.PASSED


def test_several_reports_are_evaluated_on_their_defects_alone(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies a multi-report fact set is judged by its defects, not by its size.

    Selecting which QA result is authoritative belongs to the Checkpoint 6
    context loader (ADR-004 4.4, 4.15). This rule reports what the supplied
    facts say.
    """
    task = _task(feature=feature, plan=feature_plan)
    reports = (
        _failed_report(feature, _defect(scope_task_id=task.id)),
        _final_pass(feature),
    )
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(feature=feature, reports=reports, feature_tasks=(task,))
    )
    assert result.status is RuleStatus.FAILED
    assert result.code is RuleCode.UNRESOLVED_IN_SCOPE_DEFECT
    assert result.detail("in_scope_defect_ids") == (str(reports[0].defects[0].id),)


def test_the_rule_invents_no_recency_or_ordering_mechanism(
    feature: Feature, feature_plan: FeaturePlan
) -> None:
    """Verifies report order never changes the verdict.

    If any recency, sequence, or "latest" semantics had been introduced,
    reversing the supplied reports would change the outcome. It must not: the
    authoritative-QA-result mechanism remains an open architectural question.
    """
    task = _task(feature=feature, plan=feature_plan)
    reports = (
        _failed_report(feature, _defect(scope_task_id=task.id)),
        _final_pass(feature),
    )
    rule = QAInScopeZeroDefectsRule()
    forward = rule.evaluate(_scope_context(feature=feature, reports=reports, feature_tasks=(task,)))
    reversed_order = rule.evaluate(
        _scope_context(feature=feature, reports=tuple(reversed(reports)), feature_tasks=(task,))
    )
    assert forward.status is reversed_order.status
    assert forward.code is reversed_order.code is RuleCode.UNRESOLVED_IN_SCOPE_DEFECT
    assert forward.detail("in_scope_defect_ids") == reversed_order.detail("in_scope_defect_ids")


def test_a_single_report_is_evaluated_in_full(feature: Feature, feature_plan: FeaturePlan) -> None:
    """Verifies the ADR-003 3.11 scope matrix runs when the facts are unambiguous."""
    task = _task(feature=feature, plan=feature_plan)
    result = QAInScopeZeroDefectsRule().evaluate(
        _scope_context(
            feature=feature,
            reports=(_failed_report(feature, _defect(scope_task_id=task.id)),),
            feature_tasks=(task,),
        )
    )
    assert result.code is RuleCode.UNRESOLVED_IN_SCOPE_DEFECT


def test_a_nonexistent_feature_id_is_indistinguishable_from_another_feature(
    feature: Feature,
) -> None:
    """Pins the ADR-004 4.16 capability limitation rather than claiming detection.

    The approved seven-fact context supplies only the Feature under acceptance,
    so Checkpoint 3 cannot tell a real different Feature from a nonexistent
    identifier. Both are treated as out of scope. This test exists so the
    limitation is visible and cannot be mistaken for validation.
    """
    unknown_feature_id = new_id(FeatureId)
    known_other_feature_id = new_id(FeatureId)
    rule = QAInScopeZeroDefectsRule()
    unknown = rule.evaluate(
        _scope_context(
            feature=feature,
            reports=(_failed_report(feature, _defect(scope_feature_id=unknown_feature_id)),),
        )
    )
    other = rule.evaluate(
        _scope_context(
            feature=feature,
            reports=(_failed_report(feature, _defect(scope_feature_id=known_other_feature_id)),),
        )
    )
    assert unknown.status is RuleStatus.PASSED
    assert other.status is RuleStatus.PASSED
    assert unknown.status is other.status


def test_defects_recorded_against_another_features_report_are_ignored(
    feature: Feature, coordinator_id: ActorId
) -> None:
    """Verifies only QA Reports for this Feature are considered."""
    other_feature = Feature(
        id=new_id(FeatureId),
        slug="other-feature",
        title="Other Feature",
        goal="Unrelated capability",
        coordinator_id=coordinator_id,
    )
    report = _failed_report(other_feature, _defect())
    result = QAInScopeZeroDefectsRule().evaluate(_scope_context(feature=feature, reports=(report,)))
    assert result.status is RuleStatus.PASSED
