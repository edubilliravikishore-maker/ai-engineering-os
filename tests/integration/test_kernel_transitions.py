"""The Kernel against real PostgreSQL (Blueprint 7.2, 15 Checkpoint 6).

These tests exercise the property the checkpoint exists to guarantee:

    Rejected transition = no target-state mutation + durable rejection record.

They run against the Alembic-managed schema, through the real Rule Engine and
the real state machines. Nothing is stubbed, because the invariant is about what
survives a commit and a stub commits nothing.
"""

import pytest

from ai_engineering_os.core import OSKernel
from ai_engineering_os.domain import (
    Actor,
    ActorRole,
    CapabilityType,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
    FeatureStatus,
    PlanStatus,
    new_id,
)
from ai_engineering_os.domain.event import EventType, TransitionOutcome
from ai_engineering_os.domain.plan import TaskDefinition
from ai_engineering_os.storage.unit_of_work import UnitOfWork

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------


def _feature(coordinator: Actor, *, status: FeatureStatus = FeatureStatus.PLANNED) -> Feature:
    return Feature(
        id=new_id(FeatureId),
        slug="add-login",
        title="Add login",
        goal="Let a user sign in",
        coordinator_id=coordinator.id,
        status=status,
        acceptance_criteria=("A user can sign in",),
    )


def _plan(
    feature: Feature, coordinator: Actor, *, status: PlanStatus = PlanStatus.READY
) -> FeaturePlan:
    return FeaturePlan(
        id=new_id(FeaturePlanId),
        feature_id=feature.id,
        revision_number=1,
        created_by=coordinator.id,
        status=status,
        required_capabilities=(CapabilityType.BACKEND, CapabilityType.FRONTEND),
        task_definitions=(
            TaskDefinition(
                key="sign-in-endpoint",
                title="Build the sign-in endpoint",
                capability=CapabilityType.BACKEND,
            ),
            TaskDefinition(
                key="login-form",
                title="Build the login form",
                capability=CapabilityType.FRONTEND,
                depends_on=("sign-in-endpoint",),
            ),
        ),
    )


async def _seed(uow: UnitOfWork, *actors: Actor) -> None:
    for actor in actors:
        await uow.actors.add(actor)


# --------------------------------------------------------------------------
# The core invariant
# --------------------------------------------------------------------------


async def test_a_refused_transition_leaves_the_entity_untouched_and_a_record_behind(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """The whole point of Validation-First, proven end to end.

    A Feature with no accepted Tasks cannot enter validation. The refusal must
    survive the transaction that discovered it, and the Feature must be exactly
    where it was.
    """
    await _seed(uow, coordinator)
    feature = _feature(coordinator, status=FeatureStatus.IN_PROGRESS)
    await uow.features.add(feature)
    await uow.commit()

    result = await OSKernel(uow).transition_feature(
        feature.id,
        FeatureStatus.IN_VALIDATION,
        initiator=ActorRole.COORDINATOR,
        initiator_id=coordinator.id,
    )

    assert not result.is_allowed
    assert result.rejection_reasons

    reloaded = await uow.features.get_by_id(feature.id)
    assert reloaded.status is FeatureStatus.IN_PROGRESS

    audit = await uow.transition_audit.list_by_entity(feature.id)
    assert [record.outcome for record in audit] == [TransitionOutcome.REJECTED]
    assert audit[0].reasons
    assert audit[0].attempted_state == FeatureStatus.IN_VALIDATION.value


async def test_a_structurally_undefined_transition_is_refused_before_any_rule_runs(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """The state machine refuses first, and the Rule Engine is never asked.

    Evaluating an edge's conditions when the edge does not exist would produce
    findings about a transition nobody can make.
    """
    await _seed(uow, coordinator)
    feature = _feature(coordinator, status=FeatureStatus.DRAFT)
    await uow.features.add(feature)
    await uow.commit()

    result = await OSKernel(uow).transition_feature(
        feature.id,
        FeatureStatus.ACCEPTED,
        initiator=ActorRole.COORDINATOR,
        initiator_id=coordinator.id,
    )

    assert not result.is_allowed
    assert result.rules is None
    assert all(reason["source"] == "state_machine" for reason in result.rejection_reasons)


async def test_an_unauthorised_initiator_is_refused_and_recorded(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """Authority is the state machine's question, and a refusal still records."""
    await _seed(uow, coordinator, worker)
    feature = _feature(coordinator, status=FeatureStatus.IN_PROGRESS)
    await uow.features.add(feature)
    await uow.commit()

    result = await OSKernel(uow).transition_feature(
        feature.id,
        FeatureStatus.IN_VALIDATION,
        initiator=ActorRole.WORKER,
        initiator_id=worker.id,
    )

    assert not result.is_allowed
    assert result.audit.requested_by == worker.id
    assert result.event.event_type is EventType.STATE_TRANSITION_REJECTED


# --------------------------------------------------------------------------
# Plan activation and Task instantiation (ADR-003 3.12, ADR-007 7.5)
# --------------------------------------------------------------------------


async def test_activating_a_plan_instantiates_its_tasks_in_the_same_transaction(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """Plan activation *performs* the instantiation, which is why no rule evaluates it."""
    await _seed(uow, coordinator)
    feature = _feature(coordinator)
    plan = _plan(feature, coordinator)
    await uow.features.add(feature)
    await uow.feature_plans.add(plan)
    await uow.commit()

    result = await OSKernel(uow).activate_plan(plan.id, coordinator_id=coordinator.id)

    assert result.is_allowed
    assert result.event.event_type is EventType.FEATURE_PLAN_ACTIVATED

    tasks = await uow.tasks.list_by_feature(feature.id)
    assert {task.plan_definition_key for task in tasks} == {"sign-in-endpoint", "login-form"}
    assert (await uow.features.get_by_id(feature.id)).status is FeatureStatus.IN_PROGRESS
    assert (await uow.feature_plans.get_by_id(plan.id)).status is PlanStatus.ACTIVE

    by_key = {task.plan_definition_key: task for task in tasks}
    assert by_key["login-form"].dependencies == (by_key["sign-in-endpoint"].id,)


async def test_activating_a_draft_plan_is_refused_and_creates_no_task(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """A DRAFT plan is still being written; instantiating from it would grant
    execution authority to work nobody has finished planning (ADR-003 3.12)."""
    await _seed(uow, coordinator)
    feature = _feature(coordinator)
    plan = _plan(feature, coordinator, status=PlanStatus.DRAFT)
    await uow.features.add(feature)
    await uow.feature_plans.add(plan)
    await uow.commit()

    result = await OSKernel(uow).activate_plan(plan.id, coordinator_id=coordinator.id)

    assert not result.is_allowed
    assert await uow.tasks.list_by_feature(feature.id) == ()
    assert (await uow.features.get_by_id(feature.id)).status is FeatureStatus.PLANNED
