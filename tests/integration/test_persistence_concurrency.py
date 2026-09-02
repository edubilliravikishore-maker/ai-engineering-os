"""Optimistic locking (ADR-005 5.6).

A lost update is an unverified change overwriting a verified one — the write-side
form of the failure ADR-001 exists to prevent. These tests prove the conflict is
**detected and reported**, never resolved by arrival order.
"""

import pytest

from ai_engineering_os.domain import Actor, Feature, FeatureId, FeatureStatus, new_id
from ai_engineering_os.storage.database import get_session_factory
from ai_engineering_os.storage.errors import ConcurrencyConflictError, NotFoundError
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


async def _seed(coordinator: Actor) -> Feature:
    feature = _feature(coordinator)
    factory = get_session_factory()
    async with factory() as session, UnitOfWork(session) as uow:
        await uow.actors.add(coordinator)
        await uow.features.add(feature)
        await uow.commit()
    return feature


@pytest.mark.asyncio
async def test_a_concurrent_update_is_detected_not_overwritten(
    migrated_database: None, coordinator: Actor
) -> None:
    """The second writer is rejected; the first writer's change survives intact."""
    _ = migrated_database
    feature = await _seed(coordinator)
    factory = get_session_factory()

    async with factory() as first_session, factory() as second_session:
        first = UnitOfWork(first_session)
        second = UnitOfWork(second_session)

        # Both readers see the same version.
        first_view = await first.features.get_by_id(feature.id)
        second_view = await second.features.get_by_id(feature.id)

        await first.features.save(first_view.with_status(FeatureStatus.PLANNED))
        await first.commit()

        with pytest.raises(ConcurrencyConflictError) as conflict:
            await second.features.save(second_view.with_status(FeatureStatus.IN_PROGRESS))
            await second.commit()

        assert conflict.value.entity == "Feature"
        await second.rollback()

    async with factory() as session, UnitOfWork(session) as reader:
        stored = await reader.features.get_by_id(feature.id)
        assert stored.status is FeatureStatus.PLANNED


@pytest.mark.asyncio
async def test_sequential_updates_succeed(migrated_database: None, coordinator: Actor) -> None:
    """Re-reading after a conflict is the supported path; versions advance normally."""
    _ = migrated_database
    feature = await _seed(coordinator)
    factory = get_session_factory()

    for status in (FeatureStatus.PLANNED, FeatureStatus.IN_PROGRESS, FeatureStatus.IN_VALIDATION):
        async with factory() as session, UnitOfWork(session) as uow:
            current = await uow.features.get_by_id(feature.id)
            await uow.features.save(current.with_status(status))
            await uow.commit()

    async with factory() as session, UnitOfWork(session) as reader:
        assert (await reader.features.get_by_id(feature.id)).status is (FeatureStatus.IN_VALIDATION)


@pytest.mark.asyncio
async def test_saving_an_unrecorded_entity_reports_not_found(
    migrated_database: None, coordinator: Actor
) -> None:
    """Saving something never recorded is NotFound, not a silent insert."""
    _ = migrated_database
    factory = get_session_factory()
    async with factory() as session, UnitOfWork(session) as uow:
        await uow.actors.add(coordinator)
        with pytest.raises(NotFoundError) as missing:
            await uow.features.save(_feature(coordinator))
        assert missing.value.entity == "Feature"
