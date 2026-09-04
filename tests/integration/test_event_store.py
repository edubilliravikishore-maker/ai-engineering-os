"""The append-only event stream and the transition audit ledger (ADR-006).

Two properties are pinned here that nothing else can pin:

* **Order is decided by ``sequence_number`` and by nothing else** (ADR-006 6.1).
  The ordering test deliberately writes events whose domain timestamps run
  *backwards*, because a suite that only ever writes them in order would pass
  just as happily against an implementation that sorted by ``occurred_at``.
* **The audit ledger records successes as well as refusals** (ADR-006 6.3), so
  "what happened to this entity?" is answerable from typed columns.
"""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from ai_engineering_os.domain import Actor, new_id, utc_now
from ai_engineering_os.domain.enums import ActorRole, SystemActor
from ai_engineering_os.domain.event import (
    EventType,
    OSEvent,
    TransitionAuditRecord,
    TransitionOutcome,
)
from ai_engineering_os.domain.identifiers import EventId, TaskId, TransitionAuditId
from ai_engineering_os.storage.unit_of_work import UnitOfWork

pytestmark = pytest.mark.asyncio


def _event(*, actor: Actor | None = None, aggregate_id: TaskId, occurred_at=None) -> OSEvent:
    """Builds an event attributed to ``actor``, or to the OS when none is given."""
    return OSEvent(
        id=new_id(EventId),
        event_type=EventType.TASK_STARTED if actor else EventType.STATE_TRANSITION_ALLOWED,
        aggregate_type="Task",
        aggregate_id=aggregate_id,
        actor_id=actor.id if actor else None,
        actor_role=actor.role if actor else SystemActor.OS,
        payload={"note": "n"},
        occurred_at=occurred_at or utc_now(),
    )


async def test_appending_assigns_an_increasing_sequence_the_caller_never_supplied(
    uow: UnitOfWork, worker: Actor
) -> None:
    """The database owns the ordering key (ADR-006 6.1)."""
    await uow.actors.add(worker)
    task_id = new_id(TaskId)

    first = await uow.events.add(_event(actor=worker, aggregate_id=task_id))
    second = await uow.events.add(_event(actor=worker, aggregate_id=task_id))

    assert first.sequence_number is not None
    assert second.sequence_number is not None
    assert second.sequence_number > first.sequence_number


async def test_order_follows_the_sequence_even_when_timestamps_disagree(
    uow: UnitOfWork, worker: Actor
) -> None:
    """`occurred_at` never decides order, so a skewed clock cannot reorder history."""
    await uow.actors.add(worker)
    task_id = new_id(TaskId)
    now = utc_now()

    # Appended first, but stamped an hour in the future.
    late = await uow.events.add(
        _event(actor=worker, aggregate_id=task_id, occurred_at=now + timedelta(hours=1))
    )
    # Appended second, but stamped an hour in the past.
    early = await uow.events.add(
        _event(actor=worker, aggregate_id=task_id, occurred_at=now - timedelta(hours=1))
    )

    stream = await uow.events.list_by_aggregate(task_id)
    assert [event.id for event in stream] == [late.id, early.id]
    assert [event.occurred_at for event in stream] != sorted(e.occurred_at for e in stream)


async def test_the_os_is_recorded_without_an_actor_id(uow: UnitOfWork) -> None:
    """The OS initiates transitions and has no row in `actors` (ADR-006 6.8)."""
    task_id = new_id(TaskId)
    recorded = await uow.events.add(_event(aggregate_id=task_id))

    assert recorded.actor_id is None
    assert recorded.actor_role is SystemActor.OS
    assert await uow.events.get_by_id(recorded.id) == recorded


async def test_the_database_refuses_an_actorless_event_from_a_real_role(uow: UnitOfWork) -> None:
    """The guard holds at the database, not only in the domain model (ADR-006 6.8)."""
    from ai_engineering_os.storage.models.event import OSEventRow

    uow.session.add(
        OSEventRow(
            id=new_id(EventId),
            event_type=EventType.TASK_STARTED.value,
            aggregate_type="Task",
            aggregate_id=new_id(TaskId),
            actor_id=None,
            actor_role=ActorRole.WORKER.value,
            payload={},
            occurred_at=utc_now(),
        )
    )
    with pytest.raises(IntegrityError):
        await uow.session.flush()


async def test_list_since_returns_only_what_follows_a_position(
    uow: UnitOfWork, worker: Actor
) -> None:
    """The backlog drain of ADR-006 6.6 reads strictly forward."""
    await uow.actors.add(worker)
    task_id = new_id(TaskId)

    appended = [await uow.events.add(_event(actor=worker, aggregate_id=task_id)) for _ in range(5)]
    third = appended[2].sequence_number
    assert third is not None

    remaining = await uow.events.list_since(third)
    assert [event.id for event in remaining] == [event.id for event in appended[3:]]
    assert await uow.events.list_since(0) == tuple(appended)
    assert await uow.events.latest_sequence_number() == appended[-1].sequence_number


async def test_an_empty_stream_reports_position_zero(uow: UnitOfWork) -> None:
    """A fresh subscriber has somewhere to start (ADR-006 6.6)."""
    assert await uow.events.latest_sequence_number() == 0
    assert await uow.events.list_since(0) == ()


def _audit(*, outcome: TransitionOutcome, actor: Actor, entity_id: TaskId) -> TransitionAuditRecord:
    """Builds an audit record for ``outcome``, carrying reasons only when refused."""
    return TransitionAuditRecord(
        id=new_id(TransitionAuditId),
        entity_type="Task",
        entity_id=entity_id,
        from_state="IN_PROGRESS",
        attempted_state="SUBMITTED",
        outcome=outcome,
        requested_by=actor.id,
        requested_by_role=actor.role,
        reasons=(
            ({"code": "MISSING_SYSTEM_EVIDENCE", "rule": "system_evidence_required"},)
            if outcome is TransitionOutcome.REJECTED
            else ()
        ),
    )


async def test_the_ledger_records_the_refusal_and_the_success_that_followed(
    uow: UnitOfWork, worker: Actor
) -> None:
    """Blueprint 7.2 recorded only refusals; ADR-006 6.3 records both."""
    await uow.actors.add(worker)
    task_id = new_id(TaskId)

    refused = await uow.transition_audit.add(
        _audit(outcome=TransitionOutcome.REJECTED, actor=worker, entity_id=task_id)
    )
    allowed = await uow.transition_audit.add(
        _audit(outcome=TransitionOutcome.ALLOWED, actor=worker, entity_id=task_id)
    )

    history = await uow.transition_audit.list_by_entity(task_id)
    assert [record.id for record in history] == [refused.id, allowed.id]
    assert [record.outcome for record in history] == [
        TransitionOutcome.REJECTED,
        TransitionOutcome.ALLOWED,
    ]

    assert [record.id for record in await uow.transition_audit.list_rejections_for(task_id)] == [
        refused.id
    ]


async def test_a_refusal_carries_the_reasons_it_was_refused_for(
    uow: UnitOfWork, worker: Actor
) -> None:
    """A rejection the requester cannot learn from is not an enforcement record."""
    await uow.actors.add(worker)
    task_id = new_id(TaskId)

    refused = await uow.transition_audit.add(
        _audit(outcome=TransitionOutcome.REJECTED, actor=worker, entity_id=task_id)
    )

    reloaded = await uow.transition_audit.get_by_id(refused.id)
    assert reloaded.reasons == (
        {"code": "MISSING_SYSTEM_EVIDENCE", "rule": "system_evidence_required"},
    )
    assert reloaded.from_state == "IN_PROGRESS"
    assert reloaded.attempted_state == "SUBMITTED"


async def test_the_database_refuses_a_rejection_that_records_no_reason(
    uow: UnitOfWork, worker: Actor
) -> None:
    """The domain invariant is mirrored by a CHECK, so raw SQL cannot bypass it."""
    from ai_engineering_os.storage.models.event import StateTransitionAuditRow

    await uow.actors.add(worker)
    uow.session.add(
        StateTransitionAuditRow(
            id=new_id(TransitionAuditId),
            entity_type="Task",
            entity_id=new_id(TaskId),
            from_state="IN_PROGRESS",
            attempted_state="SUBMITTED",
            outcome=TransitionOutcome.REJECTED.value,
            requested_by=worker.id,
            requested_by_role=worker.role.value,
            reasons=[],
            occurred_at=utc_now(),
        )
    )
    with pytest.raises(IntegrityError):
        await uow.session.flush()


async def test_neither_repository_offers_a_way_to_rewrite_history(uow: UnitOfWork) -> None:
    """Append-only is the absence of a code path, not a convention (ADR-005 5.8)."""
    for repository in (uow.events, uow.transition_audit):
        assert not hasattr(repository, "save")
        assert not hasattr(repository, "update")
        assert not hasattr(repository, "delete")
