"""Transaction ownership and atomicity (ADR-005 5.5).

The Unit of Work supplies the session; the **caller** decides whether the work
commits. These tests stand in for the Checkpoint 6 Kernel, which is the real
transaction owner and does not exist yet.
"""

import pytest

from ai_engineering_os.domain import (
    Actor,
    EvidenceId,
    EvidenceRecord,
    EvidenceSourceType,
    EvidenceType,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
    Task,
    TaskDefinition,
    TaskId,
    TaskRevision,
    TaskRevisionId,
    WorkPackage,
    WorkPackageId,
    new_id,
)
from ai_engineering_os.domain.enums import CapabilityType, TaskStatus
from ai_engineering_os.storage.database import get_session_factory
from ai_engineering_os.storage.errors import NotFoundError
from ai_engineering_os.storage.unit_of_work import UnitOfWork


def _feature(coordinator: Actor) -> Feature:
    return Feature(
        id=new_id(FeatureId),
        slug="user-authentication",
        title="User Authentication",
        goal="Allow users to sign in",
        coordinator_id=coordinator.id,
        acceptance_criteria=("A valid credential pair returns a session",),
    )


@pytest.mark.asyncio
async def test_uncommitted_work_is_not_visible_to_another_transaction(
    migrated_database: None, coordinator: Actor
) -> None:
    """A Unit of Work exited without commit rolls back; nothing durable is written."""
    _ = migrated_database
    factory = get_session_factory()

    async with factory() as session, UnitOfWork(session) as uow:
        await uow.actors.add(coordinator)
        await uow.features.add(_feature(coordinator))
        # deliberately no commit

    async with factory() as session, UnitOfWork(session) as reader:
        with pytest.raises(NotFoundError):
            await reader.actors.get_by_id(coordinator.id)


@pytest.mark.asyncio
async def test_committed_work_is_visible_to_another_transaction(
    migrated_database: None, coordinator: Actor
) -> None:
    """An explicitly committed Unit of Work is durable."""
    _ = migrated_database
    factory = get_session_factory()
    feature = _feature(coordinator)

    async with factory() as session, UnitOfWork(session) as uow:
        await uow.actors.add(coordinator)
        await uow.features.add(feature)
        await uow.commit()
        assert uow.is_committed

    async with factory() as session, UnitOfWork(session) as reader:
        assert await reader.features.get_by_id(feature.id) == feature


@pytest.mark.asyncio
async def test_a_submission_lands_all_or_nothing(
    migrated_database: None, coordinator: Actor, worker: Actor
) -> None:
    """Revision, Work Package, Evidence, and the Task pointer commit together.

    This is the write side of vertical-slice step 7. No rule is evaluated and no
    transition is validated here: both belong to Checkpoint 6.
    """
    _ = migrated_database
    factory = get_session_factory()
    feature = _feature(coordinator)

    async with factory() as session, UnitOfWork(session) as uow:
        await uow.actors.add(coordinator)
        await uow.actors.add(worker)
        await uow.features.add(feature)
        plan = FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=1,
            created_by=coordinator.id,
            required_capabilities=(CapabilityType.BACKEND,),
            task_definitions=(
                TaskDefinition(
                    key="auth-api",
                    title="Implement Auth API",
                    capability=CapabilityType.BACKEND,
                ),
            ),
        )
        await uow.feature_plans.add(plan)
        task = Task(
            id=new_id(TaskId),
            feature_id=feature.id,
            feature_plan_id=plan.id,
            plan_definition_key="auth-api",
            title="Implement Auth API",
            capability=CapabilityType.BACKEND,
        ).assign(worker.id)
        await uow.tasks.add(task)
        await uow.commit()

    revision_id = new_id(TaskRevisionId)
    work_package_id = new_id(WorkPackageId)

    async with factory() as session, UnitOfWork(session) as uow:
        revision = TaskRevision(
            id=revision_id,
            task_id=task.id,
            revision_number=1,
            created_by_worker_id=worker.id,
            work_package_id=work_package_id,
        )
        await uow.task_revisions.add(revision)
        work_package = WorkPackage(
            id=work_package_id,
            task_revision_id=revision_id,
            summary="Implemented the login endpoint",
        )
        await uow.work_packages.add(work_package)
        await uow.evidence.add(
            EvidenceRecord.for_inline_content(
                id=new_id(EvidenceId),
                source_type=EvidenceSourceType.SYSTEM,
                evidence_type=EvidenceType.GIT_DIFF,
                content="diff --git a/auth.py b/auth.py",
                work_package_id=work_package_id,
                verified_by_os=True,
            )
        )
        await uow.flush()
        # The active-revision pointer must move before the status: a SUBMITTED
        # Task with no active Revision is rejected by the domain itself.
        await uow.tasks.save(task.with_active_revision(1).with_status(TaskStatus.SUBMITTED))
        await uow.commit()

    async with factory() as session, UnitOfWork(session) as reader:
        stored_task = await reader.tasks.get_by_id(task.id)
        assert stored_task.status is TaskStatus.SUBMITTED
        assert stored_task.active_revision_number == 1
        history = await reader.task_revisions.get_history(task.id)
        assert len(history.revisions) == 1
        assert history.is_consistent_with(stored_task)
        assert len(await reader.evidence.list_by_work_package(work_package_id)) == 1


@pytest.mark.asyncio
async def test_a_failed_submission_leaves_nothing_behind(
    migrated_database: None, coordinator: Actor, worker: Actor
) -> None:
    """A rollback discards every record staged in the transaction, not just the last."""
    _ = migrated_database
    factory = get_session_factory()
    feature = _feature(coordinator)

    async with factory() as session, UnitOfWork(session) as uow:
        await uow.actors.add(coordinator)
        await uow.actors.add(worker)
        await uow.features.add(feature)
        plan = FeaturePlan(
            id=new_id(FeaturePlanId),
            feature_id=feature.id,
            revision_number=1,
            created_by=coordinator.id,
            required_capabilities=(CapabilityType.BACKEND,),
            task_definitions=(
                TaskDefinition(key="auth-api", title="Auth API", capability=CapabilityType.BACKEND),
            ),
        )
        await uow.feature_plans.add(plan)
        task = Task(
            id=new_id(TaskId),
            feature_id=feature.id,
            feature_plan_id=plan.id,
            plan_definition_key="auth-api",
            title="Auth API",
            capability=CapabilityType.BACKEND,
        )
        await uow.tasks.add(task)
        await uow.commit()

    async with factory() as session, UnitOfWork(session) as uow:
        await uow.task_revisions.add(
            TaskRevision(
                id=new_id(TaskRevisionId),
                task_id=task.id,
                revision_number=1,
                created_by_worker_id=worker.id,
            )
        )
        await uow.rollback()

    async with factory() as session, UnitOfWork(session) as reader:
        assert (await reader.task_revisions.get_history(task.id)).revisions == ()
