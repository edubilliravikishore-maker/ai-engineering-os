"""Domain reconstruction fails rather than repairing (ADR-005 5.3, 5.20).

A stored row that no longer forms a valid domain object must raise. Silent repair
would let an invalid state re-enter the system through persistence, which
ADR-002's testing principles require to be unreachable through normal OS
interfaces.

These tests write rows with raw SQL on purpose: they must produce data the
repository would never write, so the guard is exercised rather than assumed.
"""

import pytest
from sqlalchemy import text

from ai_engineering_os.domain import Actor, new_id
from ai_engineering_os.domain.identifiers import FeatureId, QAReportId
from ai_engineering_os.storage.errors import DomainReconstructionError
from ai_engineering_os.storage.unit_of_work import UnitOfWork


async def _insert_actor(uow: UnitOfWork, actor: Actor) -> None:
    await uow.actors.add(actor)
    await uow.flush()


@pytest.mark.asyncio
async def test_a_row_violating_a_domain_invariant_fails_to_reconstruct(
    uow: UnitOfWork, coordinator: Actor
) -> None:
    """A PLANNED Feature with no acceptance criteria is rejected, not returned.

    The database has no constraint for this: it is a domain invariant, and
    business rules deliberately stay in the domain (ADR-005 5.14).
    """
    await _insert_actor(uow, coordinator)
    feature_id = new_id(FeatureId)
    await uow.session.execute(
        text(
            "INSERT INTO features (id, slug, title, goal, coordinator_id, status, "
            "requirements, in_scope, out_of_scope, acceptance_criteria, qa_round, "
            "created_at, updated_at, version) "
            "VALUES (:id, 'broken', 't', 'g', :coordinator, 'PLANNED', "
            "'[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 1, now(), now(), 1)"
        ),
        {"id": feature_id, "coordinator": coordinator.id},
    )

    with pytest.raises(DomainReconstructionError) as failure:
        await uow.features.get_by_id(feature_id)

    assert failure.value.entity == "Feature"
    assert failure.value.entity_id == feature_id


@pytest.mark.asyncio
async def test_reconstruction_does_not_silently_repair(uow: UnitOfWork, coordinator: Actor) -> None:
    """A PASSED QA Report carrying an unresolved defect raises rather than dropping it."""
    await _insert_actor(uow, coordinator)
    feature_id = new_id(FeatureId)
    await uow.session.execute(
        text(
            "INSERT INTO features (id, slug, title, goal, coordinator_id, status, "
            "requirements, in_scope, out_of_scope, acceptance_criteria, qa_round, "
            "created_at, updated_at, version) "
            "VALUES (:id, 'f', 't', 'g', :coordinator, 'DRAFT', "
            "'[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 1, now(), now(), 1)"
        ),
        {"id": feature_id, "coordinator": coordinator.id},
    )
    report_id = new_id(QAReportId)
    await uow.session.execute(
        text(
            "INSERT INTO qa_reports (id, feature_id, status, qa_round, is_final_pass, "
            "tested_scope, results, evidence_ids, created_at) "
            "VALUES (:id, :feature, 'PASSED', 1, false, '[]'::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, now())"
        ),
        {"id": report_id, "feature": feature_id},
    )
    await uow.session.execute(
        text(
            "INSERT INTO qa_defects (id, qa_report_id, position, title, severity, priority, "
            "is_blocker, status) "
            "VALUES (gen_random_uuid(), :report, 0, 'still open', 'high', 'p1', true, 'OPEN')"
        ),
        {"report": report_id},
    )

    with pytest.raises(DomainReconstructionError) as failure:
        await uow.qa_reports.get_by_id(report_id)

    assert failure.value.entity == "QAReport"


@pytest.mark.asyncio
async def test_a_valid_row_reconstructs_normally(uow: UnitOfWork, coordinator: Actor) -> None:
    """The guard does not fire on well-formed data."""
    await _insert_actor(uow, coordinator)
    assert await uow.actors.get_by_id(coordinator.id) == coordinator
