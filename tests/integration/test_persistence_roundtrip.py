"""Round-trip fidelity: a domain object stored and reloaded is identical.

This is the load-bearing property of ADR-005 5.3 and 5.11. If a round trip loses
or reorders anything, every fact the Checkpoint 6 context loader supplies to the
Rule Engine would be subtly wrong.
"""

from datetime import UTC, datetime

import pytest

from ai_engineering_os.domain import (
    Actor,
    Claim,
    ClaimId,
    Decision,
    DecisionId,
    DecisionScope,
    EvidenceId,
    EvidenceMetadata,
    EvidenceRecord,
    EvidenceSourceType,
    EvidenceType,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
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
    VerificationGuide,
    WorkPackage,
    WorkPackageId,
    new_id,
)
from ai_engineering_os.domain import (
    TestResult as QATestResult,
)
from ai_engineering_os.domain.enums import ActorRole, CapabilityType
from ai_engineering_os.storage.unit_of_work import UnitOfWork


async def _seed_feature(uow: UnitOfWork, coordinator: Actor) -> Feature:
    """Records a Coordinator and a Feature it owns."""
    await uow.actors.add(coordinator)
    feature = Feature(
        id=new_id(FeatureId),
        slug="user-authentication",
        title="User Authentication via Email/Password",
        goal="Allow users to sign in with an email address and password",
        coordinator_id=coordinator.id,
        requirements=("Email/password login",),
        in_scope=("Email/password login", "Forgot password reset flow"),
        out_of_scope=("Google OAuth", "Phone OTP"),
        acceptance_criteria=("A valid credential pair returns an authenticated session",),
    )
    await uow.features.add(feature)
    return feature


async def _seed_plan(uow: UnitOfWork, feature: Feature, coordinator: Actor) -> FeaturePlan:
    """Records a two-node Feature Plan against ``feature``."""
    plan = FeaturePlan(
        id=new_id(FeaturePlanId),
        feature_id=feature.id,
        revision_number=1,
        created_by=coordinator.id,
        required_capabilities=(CapabilityType.BACKEND, CapabilityType.QA),
        task_definitions=(
            TaskDefinition(
                key="auth-api", title="Implement Auth API", capability=CapabilityType.BACKEND
            ),
            TaskDefinition(
                key="auth-qa",
                title="Validate Auth API",
                capability=CapabilityType.QA,
                depends_on=("auth-api",),
            ),
        ),
    )
    await uow.feature_plans.add(plan)
    return plan


@pytest.mark.asyncio
async def test_actor_round_trips_identically(uow: UnitOfWork, worker: Actor) -> None:
    """An Actor, including its capability set, survives a round trip unchanged."""
    await uow.actors.add(worker)
    assert await uow.actors.get_by_id(worker.id) == worker


@pytest.mark.asyncio
async def test_feature_round_trips_with_scope_lists(uow: UnitOfWork, coordinator: Actor) -> None:
    """A Feature's four ordered text lists survive a round trip in order."""
    feature = await _seed_feature(uow, coordinator)
    assert await uow.features.get_by_id(feature.id) == feature


@pytest.mark.asyncio
async def test_feature_is_retrievable_by_slug(uow: UnitOfWork, coordinator: Actor) -> None:
    """A Feature can be found by its recorded slug."""
    feature = await _seed_feature(uow, coordinator)
    assert await uow.features.get_by_slug("user-authentication") == feature


@pytest.mark.asyncio
async def test_plan_round_trips_with_ordered_definitions(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """Plan-local task definitions round trip in their recorded order."""
    feature = await _seed_feature(uow, coordinator)
    plan = await _seed_plan(uow, feature, coordinator)

    reloaded = await uow.feature_plans.get_by_id(plan.id)
    assert reloaded == plan
    assert [d.key for d in reloaded.task_definitions] == ["auth-api", "auth-qa"]
    assert reloaded.task_definitions[1].depends_on == ("auth-api",)


@pytest.mark.asyncio
async def test_task_round_trips_with_ordered_dependencies(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """A Task's prerequisite tuple round trips in order, with plan linkage intact."""
    feature = await _seed_feature(uow, coordinator)
    plan = await _seed_plan(uow, feature, coordinator)

    first = Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="auth-api",
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
    )
    await uow.tasks.add(first)

    second = Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="auth-qa",
        title="Validate Auth API",
        capability=CapabilityType.QA,
        dependencies=(first.id,),
    )
    await uow.tasks.add(second)

    reloaded = await uow.tasks.get_by_id(second.id)
    assert reloaded == second
    assert reloaded.dependencies == (first.id,)
    assert reloaded.feature_plan_id == plan.id
    assert reloaded.plan_definition_key == "auth-qa"


@pytest.mark.asyncio
async def test_tasks_are_readable_in_bulk_and_by_feature(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """Bulk reads exist because the referenced_tasks fact needs them (ADR-005 5.4)."""
    feature = await _seed_feature(uow, coordinator)
    plan = await _seed_plan(uow, feature, coordinator)
    created = []
    for index, key in enumerate(("auth-api", "auth-qa")):
        task = Task(
            id=new_id(TaskId),
            feature_id=feature.id,
            feature_plan_id=plan.id,
            plan_definition_key=key,
            title=f"Task {index}",
            capability=CapabilityType.BACKEND,
            created_at=datetime(2026, 9, 1, 10, index, tzinfo=UTC),
            updated_at=datetime(2026, 9, 1, 10, index, tzinfo=UTC),
        )
        await uow.tasks.add(task)
        created.append(task)

    assert set(await uow.tasks.list_by_feature(feature.id)) == set(created)
    assert await uow.tasks.get_many_by_id([created[1].id, created[0].id]) == (
        created[1],
        created[0],
    )
    assert await uow.tasks.get_many_by_id([]) == ()


@pytest.mark.asyncio
async def test_revision_history_is_contiguous_and_ordered(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """Revision history is assembled by revision number, never by a metadata timestamp."""
    feature = await _seed_feature(uow, coordinator)
    plan = await _seed_plan(uow, feature, coordinator)
    await uow.actors.add(worker)
    task = Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="auth-api",
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
    )
    await uow.tasks.add(task)

    for number in (1, 2, 3):
        await uow.task_revisions.add(
            TaskRevision(
                id=new_id(TaskRevisionId),
                task_id=task.id,
                revision_number=number,
                created_by_worker_id=worker.id,
            )
        )

    history = await uow.task_revisions.get_history(task.id)
    assert [r.revision_number for r in history.revisions] == [1, 2, 3]
    assert history.next_revision_number == 4
    assert history.active_revision is not None
    assert history.active_revision.revision_number == 3


@pytest.mark.asyncio
async def test_work_package_and_evidence_round_trip(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """A Work Package's claims, guide, and attached Evidence survive a round trip."""
    feature = await _seed_feature(uow, coordinator)
    plan = await _seed_plan(uow, feature, coordinator)
    await uow.actors.add(worker)
    task = Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="auth-api",
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
    )
    await uow.tasks.add(task)
    revision = TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=task.id,
        revision_number=1,
        created_by_worker_id=worker.id,
    )
    await uow.task_revisions.add(revision)

    work_package = WorkPackage(
        id=new_id(WorkPackageId),
        task_revision_id=revision.id,
        summary="Implemented the email/password login endpoint",
        claims=(
            Claim(
                id=new_id(ClaimId),
                claim_type="API_IMPLEMENTED",
                description="Login API implemented",
            ),
        ),
        verification_guide=VerificationGuide(
            steps=("POST /auth/login with valid credentials",),
            endpoints=("POST /auth/login",),
            expected_outputs=("200 OK with a session token",),
        ),
        worker_notes=("Chose bcrypt over argon2 for parity with the existing store",),
        risks="Rate limiting is not yet applied",
    )
    await uow.work_packages.add(work_package)

    evidence = EvidenceRecord.for_inline_content(
        id=new_id(EvidenceId),
        source_type=EvidenceSourceType.SYSTEM,
        evidence_type=EvidenceType.GIT_DIFF,
        content="diff --git a/auth.py b/auth.py",
        work_package_id=work_package.id,
        metadata=EvidenceMetadata(command="git diff", exit_code=0, git_hash="abc123"),
        verified_by_os=True,
    )
    await uow.evidence.add(evidence)

    assert await uow.work_packages.get_by_id(work_package.id) == work_package
    assert await uow.work_packages.get_by_task_revision(revision.id) == work_package
    assert await uow.evidence.list_by_work_package(work_package.id) == (evidence,)


@pytest.mark.asyncio
async def test_qa_report_round_trips_with_defect_scope(uow: UnitOfWork, coordinator: Actor) -> None:
    """QA defects round trip in order, including the both-null unresolved scope."""
    feature = await _seed_feature(uow, coordinator)
    plan = await _seed_plan(uow, feature, coordinator)
    task = Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="auth-api",
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
    )
    await uow.tasks.add(task)

    report = QAReport(
        id=new_id(QAReportId),
        feature_id=feature.id,
        status=QAStatus.FAILED,
        tested_scope=("Login endpoint",),
        results=(QATestResult(name="test_login_success", passed=False, details="401 returned"),),
        defects=(
            QADefect(
                id=new_id(QADefectId),
                title="Valid credentials rejected",
                severity="high",
                priority="p1",
                is_blocker=True,
                scope_task_id=task.id,
            ),
            QADefect(
                id=new_id(QADefectId),
                title="Unclear error copy",
                severity="low",
                priority="p3",
                scope_feature_id=feature.id,
            ),
            QADefect(
                id=new_id(QADefectId),
                title="Scope not yet determined",
                severity="low",
                priority="p3",
            ),
        ),
    )
    await uow.qa_reports.add(report)

    reloaded = await uow.qa_reports.get_by_id(report.id)
    assert reloaded == report
    assert reloaded.defects[0].scope_task_id == task.id
    assert reloaded.defects[1].scope_feature_id == feature.id
    assert reloaded.defects[2].scope_task_id is None
    assert reloaded.defects[2].scope_feature_id is None


@pytest.mark.asyncio
async def test_review_decision_round_trips(
    uow: UnitOfWork, coordinator: Actor, worker: Actor, reviewer: Actor
) -> None:
    """A Reviewer outcome and its mandatory notes survive a round trip."""
    feature = await _seed_feature(uow, coordinator)
    plan = await _seed_plan(uow, feature, coordinator)
    await uow.actors.add(worker)
    await uow.actors.add(reviewer)
    task = Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="auth-api",
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
    )
    await uow.tasks.add(task)
    revision = TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=task.id,
        revision_number=1,
        created_by_worker_id=worker.id,
    )
    await uow.task_revisions.add(revision)

    review = ReviewDecision(
        id=new_id(ReviewDecisionId),
        task_revision_id=revision.id,
        reviewer_id=reviewer.id,
        outcome=ReviewOutcome.APPROVED,
        notes="Evidence supports every claim; the diff matches the described change",
    )
    await uow.review_decisions.add(review)

    assert await uow.review_decisions.get_by_id(review.id) == review
    assert await uow.review_decisions.get_by_task_revision(revision.id) == review


@pytest.mark.asyncio
async def test_decision_acknowledgement_is_appended_not_rewritten(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """An acknowledgement is appended as a child row; the Decision is never rewritten."""
    await uow.actors.add(coordinator)
    decision = Decision(
        id=new_id(DecisionId),
        scope=DecisionScope.FEATURE,
        decided_by_role=ActorRole.COORDINATOR,
        decided_by_id=coordinator.id,
        problem="Which password hash should the auth service use?",
        decision_text="Use bcrypt",
        reasoning="Parity with the existing credential store",
        alternatives_considered=("argon2", "scrypt"),
        affected_domains=("auth",),
    )
    await uow.decisions.add(decision)
    assert await uow.decisions.get_by_id(decision.id) == decision

    updated = await uow.decisions.add_acknowledgement(
        decision.id, actor_id=coordinator.id, actor_role=ActorRole.COORDINATOR
    )
    reloaded = await uow.decisions.get_by_id(decision.id)
    assert reloaded == updated
    assert reloaded.is_acknowledged_by(coordinator.id)
    assert reloaded.decision_text == decision.decision_text
