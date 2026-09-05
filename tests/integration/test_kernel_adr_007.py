"""The ADR-007 checks that are not enforced by construction.

ADR-007 records four rulings and, for two of them, records honestly that
correctness rests on the Kernel doing exactly one thing in exactly one place.
That is the same class of risk ADR-006 6.9 recorded for the notification emit,
and it needs the same treatment: a test that fails when the discipline slips.

Every test here corresponds to a named required check in
[brain/Current-Focus.md](../../brain/Current-Focus.md).
"""

import pytest

from ai_engineering_os.core import OSKernel
from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
    FeatureStatus,
    PlanStatus,
    QAReport,
    QAReportId,
    QAStatus,
    Task,
    TaskId,
    TaskRevision,
    TaskRevisionId,
    TaskStatus,
    new_id,
)
from ai_engineering_os.domain.plan import TaskDefinition
from ai_engineering_os.rules.codes import RuleCode
from ai_engineering_os.storage.unit_of_work import UnitOfWork

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------


def _feature(coordinator: Actor, *, status: FeatureStatus, qa_round: int = 1) -> Feature:
    return Feature(
        id=new_id(FeatureId),
        slug="add-login",
        title="Add login",
        goal="Let a user sign in",
        coordinator_id=coordinator.id,
        status=status,
        qa_round=qa_round,
        acceptance_criteria=("A user can sign in",),
    )


def _plan(feature: Feature, coordinator: Actor) -> FeaturePlan:
    return FeaturePlan(
        id=new_id(FeaturePlanId),
        feature_id=feature.id,
        revision_number=1,
        created_by=coordinator.id,
        status=PlanStatus.ACTIVE,
        required_capabilities=(CapabilityType.BACKEND,),
        task_definitions=(
            TaskDefinition(
                key="sign-in-endpoint",
                title="Build the sign-in endpoint",
                capability=CapabilityType.BACKEND,
            ),
        ),
    )


def _task(feature: Feature, plan: FeaturePlan, worker: Actor) -> Task:
    return Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=plan.id,
        plan_definition_key="sign-in-endpoint",
        title="Build the sign-in endpoint",
        capability=CapabilityType.BACKEND,
        status=TaskStatus.SUBMITTED,
        assigned_worker_id=worker.id,
        active_revision_number=1,
    )


async def _seed_submitted_task(
    uow: UnitOfWork, coordinator: Actor, worker: Actor, *reviewers: Actor
) -> Task:
    """Records a Feature, an ACTIVE Plan and one SUBMITTED Task with a Revision."""
    for actor in (coordinator, worker, *reviewers):
        await uow.actors.add(actor)
    feature = _feature(coordinator, status=FeatureStatus.IN_PROGRESS)
    plan = _plan(feature, coordinator)
    task = _task(feature, plan, worker)
    await uow.features.add(feature)
    await uow.feature_plans.add(plan)
    await uow.tasks.add(task)
    await uow.task_revisions.add(
        TaskRevision(
            id=new_id(TaskRevisionId),
            task_id=task.id,
            revision_number=1,
            created_by_worker_id=worker.id,
        )
    )
    await uow.commit()
    return task


def _reviewer(name: str, *, capability: CapabilityType = CapabilityType.BACKEND) -> Actor:
    return Actor(
        id=new_id(ActorId),
        role=ActorRole.REVIEWER,
        name=name,
        capabilities=frozenset({capability}),
    )


# --------------------------------------------------------------------------
# 7.3 — a Worker never reviews their own work
# --------------------------------------------------------------------------


async def test_a_submitted_task_is_routed_to_an_eligible_reviewer(
    uow: UnitOfWork, coordinator: Actor, worker: Actor, reviewer: Actor
) -> None:
    """The ordinary path: one eligible Reviewer, and the Task reaches review."""
    task = await _seed_submitted_task(uow, coordinator, worker, reviewer)

    result = await OSKernel(uow).route_for_review(task.id)

    assert result.is_allowed
    routed = await uow.tasks.get_by_id(task.id)
    assert routed.status is TaskStatus.IN_REVIEW
    assert routed.reviewer_id == reviewer.id


async def test_the_assigned_worker_is_never_routed_their_own_task(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """ADR-001, made enforceable by ADR-007 7.3.

    The Worker is registered as a Reviewer too and is the only candidate. The OS
    must refuse rather than route the work back to the person who did it.
    """
    reviewing_worker = Actor(
        id=worker.id,
        role=ActorRole.REVIEWER,
        name=worker.name,
        capabilities=frozenset({CapabilityType.BACKEND}),
    )
    for actor in (coordinator, reviewing_worker):
        await uow.actors.add(actor)
    feature = _feature(coordinator, status=FeatureStatus.IN_PROGRESS)
    plan = _plan(feature, coordinator)
    task = _task(feature, plan, reviewing_worker)
    await uow.features.add(feature)
    await uow.feature_plans.add(plan)
    await uow.tasks.add(task)
    await uow.commit()

    result = await OSKernel(uow).route_for_review(task.id)

    assert not result.is_allowed
    assert (await uow.tasks.get_by_id(task.id)).status is TaskStatus.SUBMITTED
    assert (await uow.tasks.get_by_id(task.id)).reviewer_id is None


async def test_an_earlier_revision_author_is_never_routed_the_task(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """A Task can change hands, and a previous author is still disqualified.

    This is the case only the Rule Engine and the router can catch: the Task
    model and the database constraint compare against the *current* assignment,
    and this Actor is no longer it.
    """
    previous_author = _reviewer("previous-author")
    for actor in (coordinator, worker, previous_author):
        await uow.actors.add(actor)
    feature = _feature(coordinator, status=FeatureStatus.IN_PROGRESS)
    plan = _plan(feature, coordinator)
    task = _task(feature, plan, worker)
    await uow.features.add(feature)
    await uow.feature_plans.add(plan)
    await uow.tasks.add(task)
    await uow.task_revisions.add(
        TaskRevision(
            id=new_id(TaskRevisionId),
            task_id=task.id,
            revision_number=1,
            created_by_worker_id=previous_author.id,
        )
    )
    await uow.commit()

    result = await OSKernel(uow).route_for_review(task.id)

    assert not result.is_allowed
    assert (await uow.tasks.get_by_id(task.id)).reviewer_id is None


async def test_no_eligible_reviewer_refuses_with_a_reason_naming_the_cause(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """Failing closed is the intended behaviour, and a stall must be diagnosable.

    ADR-007 7.3 records the trade-off explicitly: a Feature can stall at
    ``SUBMITTED`` on an Actor-registry problem, and the refusal reason must name
    the cause or the stall will be hard to diagnose.
    """
    frontend_only = _reviewer("frontend-reviewer", capability=CapabilityType.FRONTEND)
    task = await _seed_submitted_task(uow, coordinator, worker, frontend_only)

    result = await OSKernel(uow).route_for_review(task.id)

    assert not result.is_allowed
    codes = {reason["code"] for reason in result.rejection_reasons}
    assert RuleCode.NO_REVIEWER_ROUTED.value in codes

    audit = await uow.transition_audit.list_by_entity(task.id)
    assert audit and audit[-1].reasons


async def test_routing_is_deterministic_and_takes_the_lowest_identifier(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """The ADR-007 7.3 tie-break: deterministic, and recorded as not fair."""
    reviewers = [_reviewer(f"reviewer-{index}") for index in range(3)]
    task = await _seed_submitted_task(uow, coordinator, worker, *reviewers)

    result = await OSKernel(uow).route_for_review(task.id)

    assert result.is_allowed
    expected = min(reviewer.id for reviewer in reviewers)
    assert (await uow.tasks.get_by_id(task.id)).reviewer_id == expected


# --------------------------------------------------------------------------
# 7.4 — the QA round advances on exactly one transition
# --------------------------------------------------------------------------


async def test_returning_a_feature_for_rework_advances_the_qa_round(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """The rework loop is the one transition that opens a new round."""
    await uow.actors.add(coordinator)
    feature = _feature(coordinator, status=FeatureStatus.IN_VALIDATION)
    await uow.features.add(feature)
    await uow.commit()

    result = await OSKernel(uow).return_for_rework(
        feature.id, initiator=ActorRole.QA, initiator_id=coordinator.id
    )

    assert result.is_allowed
    reloaded = await uow.features.get_by_id(feature.id)
    assert reloaded.status is FeatureStatus.IN_PROGRESS
    assert reloaded.qa_round == 2


async def test_no_other_transition_touches_the_qa_round(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """The check ADR-007 7.4 asks for by name.

    Correctness rests on exactly one Kernel increment on exactly one transition,
    and that is **not enforced by construction**. Every other Feature transition
    the slice walks is run here and the round must not move.
    """
    await uow.actors.add(coordinator)
    feature = _feature(coordinator, status=FeatureStatus.PLANNED)
    plan = _plan(feature, coordinator)
    await uow.features.add(feature)
    await uow.feature_plans.add(plan.with_status(PlanStatus.READY))
    await uow.commit()

    kernel = OSKernel(uow)
    await kernel.activate_plan(plan.id, coordinator_id=coordinator.id)
    assert (await uow.features.get_by_id(feature.id)).qa_round == 1

    # A refused transition must not move it either.
    await kernel.transition_feature(
        feature.id,
        FeatureStatus.IN_VALIDATION,
        initiator=ActorRole.COORDINATOR,
        initiator_id=coordinator.id,
    )
    assert (await uow.features.get_by_id(feature.id)).qa_round == 1


async def test_a_qa_report_is_stamped_with_the_features_current_round(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """The round is stamped at recording, from the Feature's own field.

    Never supplied by the reporting Actor: the report below claims round 99 and
    is recorded in the round the Feature is actually in.
    """
    await uow.actors.add(coordinator)
    feature = _feature(coordinator, status=FeatureStatus.IN_VALIDATION, qa_round=3)
    await uow.features.add(feature)
    await uow.commit()

    recorded = await OSKernel(uow).record_qa_report(
        QAReport(
            id=new_id(QAReportId),
            feature_id=feature.id,
            status=QAStatus.PASSED,
            qa_round=99,
        )
    )
    await uow.commit()

    assert recorded.qa_round == 3
    stored = await uow.qa_reports.list_by_feature(feature.id)
    assert [report.qa_round for report in stored] == [3]


async def test_a_late_report_from_an_earlier_round_stays_in_that_round(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """Stamping at recording time is what makes this automatic.

    A report written during round 1 but submitted after rework has begun belongs
    to round 1 if it was recorded before the rework, and to round 2 if after.
    Nothing depends on when anybody wrote it.
    """
    await uow.actors.add(coordinator)
    feature = _feature(coordinator, status=FeatureStatus.IN_VALIDATION)
    await uow.features.add(feature)
    await uow.commit()

    kernel = OSKernel(uow)
    first = await kernel.record_qa_report(
        QAReport(id=new_id(QAReportId), feature_id=feature.id, status=QAStatus.PASSED)
    )
    await uow.commit()

    await kernel.return_for_rework(feature.id, initiator=ActorRole.QA, initiator_id=coordinator.id)

    second = await kernel.record_qa_report(
        QAReport(id=new_id(QAReportId), feature_id=feature.id, status=QAStatus.PASSED)
    )
    await uow.commit()

    assert first.qa_round == 1
    assert second.qa_round == 2
    assert (await uow.qa_reports.get_by_id(first.id)).qa_round == 1
