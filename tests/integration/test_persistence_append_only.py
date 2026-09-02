"""Append-only storage and the Work Package hybrid (ADR-005 5.7, 5.8).

Append-only is enforced **by construction**: an append-only repository exposes no
update method at all, so no code path capable of rewriting history exists. These
tests pin that property, because a future refactor that "helpfully" adds a save
method would silently remove an architectural guarantee.
"""

import pytest

from ai_engineering_os.domain import (
    Actor,
    Claim,
    ClaimId,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
    Task,
    TaskDefinition,
    TaskId,
    TaskRevision,
    TaskRevisionId,
    VerificationGuide,
    WorkPackage,
    WorkPackageId,
    new_id,
    utc_now,
)
from ai_engineering_os.domain.enums import CapabilityType, WorkPackageStatus
from ai_engineering_os.storage.errors import AppendOnlyViolationError
from ai_engineering_os.storage.repositories import (
    ActorRepository,
    DecisionRepository,
    EvidenceRepository,
    FeaturePlanRepository,
    FeatureRepository,
    QAReportRepository,
    ReviewDecisionRepository,
    TaskRepository,
    TaskRevisionRepository,
    WorkPackageRepository,
)
from ai_engineering_os.storage.unit_of_work import UnitOfWork

APPEND_ONLY_REPOSITORIES = (
    TaskRevisionRepository,
    EvidenceRepository,
    QAReportRepository,
    ReviewDecisionRepository,
    DecisionRepository,
)

MUTABLE_REPOSITORIES = (
    ActorRepository,
    FeatureRepository,
    FeaturePlanRepository,
    TaskRepository,
    WorkPackageRepository,
)

ALL_REPOSITORIES = APPEND_ONLY_REPOSITORIES + MUTABLE_REPOSITORIES


@pytest.mark.parametrize("repository", APPEND_ONLY_REPOSITORIES)
def test_append_only_repositories_expose_no_update(repository: type) -> None:
    """A historical record has no update path, so it cannot be rewritten."""
    assert not hasattr(repository, "save")
    assert not hasattr(repository, "update")


@pytest.mark.parametrize("repository", ALL_REPOSITORIES)
def test_no_repository_exposes_delete(repository: type) -> None:
    """There is no generic delete capability anywhere (ADR-005 5.7)."""
    for forbidden in ("delete", "remove", "destroy", "purge", "truncate"):
        assert not hasattr(repository, forbidden), f"{repository.__name__}.{forbidden} exists"


@pytest.mark.parametrize("repository", ALL_REPOSITORIES)
def test_no_repository_commits(repository: type) -> None:
    """The service/use-case layer owns the transaction boundary (ADR-005 5.5)."""
    assert not hasattr(repository, "commit")
    assert not hasattr(repository, "rollback")


async def _submitted_work_package(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> WorkPackage:
    """Records a Work Package that has already been submitted."""
    await uow.actors.add(coordinator)
    await uow.actors.add(worker)
    feature = Feature(
        id=new_id(FeatureId),
        slug="user-authentication",
        title="User Authentication",
        goal="Allow users to sign in",
        coordinator_id=coordinator.id,
        acceptance_criteria=("A valid credential pair returns a session",),
    )
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
    revision = TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=task.id,
        revision_number=1,
        created_by_worker_id=worker.id,
    )
    await uow.task_revisions.add(revision)
    draft = WorkPackage(
        id=new_id(WorkPackageId),
        task_revision_id=revision.id,
        summary="Implemented the login endpoint",
        claims=(Claim(id=new_id(ClaimId), claim_type="API_IMPLEMENTED", description="done"),),
        verification_guide=VerificationGuide(steps=("POST /auth/login",)),
    )
    await uow.work_packages.add(draft)
    submitted = draft.submit(at=utc_now())
    await uow.work_packages.save(submitted)
    return submitted


@pytest.mark.asyncio
async def test_draft_work_package_content_remains_editable(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """While DRAFT, recorded content may still change (ADR-005 5.8)."""
    await uow.actors.add(coordinator)
    await uow.actors.add(worker)
    feature = Feature(
        id=new_id(FeatureId),
        slug="user-authentication",
        title="User Authentication",
        goal="Allow users to sign in",
        coordinator_id=coordinator.id,
        acceptance_criteria=("A valid credential pair returns a session",),
    )
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
    revision = TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=task.id,
        revision_number=1,
        created_by_worker_id=worker.id,
    )
    await uow.task_revisions.add(revision)

    draft = WorkPackage(
        id=new_id(WorkPackageId),
        task_revision_id=revision.id,
        summary="First pass",
    )
    await uow.work_packages.add(draft)
    await uow.work_packages.save(draft.revise_draft(summary="Second pass"))

    assert (await uow.work_packages.get_by_id(draft.id)).summary == "Second pass"


@pytest.mark.asyncio
async def test_submitted_work_package_content_is_frozen(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """Once submitted, recorded content cannot be rewritten (ADR-005 5.8)."""
    submitted = await _submitted_work_package(uow, coordinator, worker)
    assert submitted.status is WorkPackageStatus.SUBMITTED

    tampered = submitted.model_copy(update={"summary": "Rewritten after the fact"})
    with pytest.raises(AppendOnlyViolationError) as violation:
        await uow.work_packages.save(tampered)

    assert violation.value.record_type == "WorkPackage"
    assert "summary" in violation.value.fields
    assert (await uow.work_packages.get_by_id(submitted.id)).summary == submitted.summary


@pytest.mark.asyncio
async def test_submitted_work_package_status_still_projects(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """Status still moves after submission: it is an OS projection (ADR-003 3.5).

    The repository persists whatever status the approved lifecycle transitions
    have established. It neither decides one nor blocks one.
    """
    submitted = await _submitted_work_package(uow, coordinator, worker)

    for status in (
        WorkPackageStatus.VALIDATED,
        WorkPackageStatus.REVIEWED,
        WorkPackageStatus.ACCEPTED,
    ):
        await uow.work_packages.save(submitted.with_status(status))
        assert (await uow.work_packages.get_by_id(submitted.id)).status is status


@pytest.mark.asyncio
async def test_recorded_revisions_are_never_rewritten(
    uow: UnitOfWork, coordinator: Actor, worker: Actor
) -> None:
    """Appending a Revision leaves every earlier Revision untouched."""
    submitted = await _submitted_work_package(uow, coordinator, worker)
    first = await uow.task_revisions.get_by_id(submitted.task_revision_id)

    second = TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=first.task_id,
        revision_number=2,
        created_by_worker_id=worker.id,
    )
    await uow.task_revisions.add(second)

    history = await uow.task_revisions.get_history(first.task_id)
    assert [r.revision_number for r in history.revisions] == [1, 2]
    assert history.revisions[0] == first
