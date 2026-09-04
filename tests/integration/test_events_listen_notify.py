"""The notification bus and the subscriber (ADR-006 6.2, 6.6, 6.7).

Three claims are verified here, and each would be untrue under a plausible
alternative implementation:

* **A notification is delivered only if the transaction that queued it commits**
  (ADR-006 6.2). The rollback test is the one that matters: an emit issued after
  ``commit()`` would pass the happy-path test and fail this one.
* **A subscriber resumes from its position rather than from the signal**
  (ADR-006 6.6), so events appended while nobody was listening are still
  processed, in order.
* **The wake-up carries an identifier, never a domain object** (Blueprint 14,
  item 3).
"""

import asyncio

import pytest

from ai_engineering_os.domain import new_id, utc_now
from ai_engineering_os.domain.enums import SystemActor
from ai_engineering_os.domain.event import EventType, OSEvent
from ai_engineering_os.domain.identifiers import EventId, TaskId
from ai_engineering_os.events import (
    NOTIFY_PAYLOAD_LIMIT_BYTES,
    OS_EVENTS_CHANNEL,
    EventSubscriber,
    NotificationEnvelope,
    emit_for_event,
)
from ai_engineering_os.storage.unit_of_work import unit_of_work

pytestmark = pytest.mark.asyncio

WAKE_TIMEOUT = 5.0
"""Generous enough for a real round trip, short enough that a hang fails."""

QUIET_TIMEOUT = 1.0
"""How long to wait before concluding that no notification is coming."""


class Collector:
    """Records what the subscriber handed it, and signals each arrival."""

    def __init__(self) -> None:
        self.received: list[OSEvent] = []
        self.arrived = asyncio.Event()

    async def __call__(self, event: OSEvent) -> None:
        self.received.append(event)
        self.arrived.set()

    async def wait_for(self, count: int, *, timeout: float = WAKE_TIMEOUT) -> None:
        """Waits until ``count`` events have arrived, or fails the test."""

        async def _poll() -> None:
            while len(self.received) < count:
                self.arrived.clear()
                await self.arrived.wait()

        await asyncio.wait_for(_poll(), timeout=timeout)


def _event(*, aggregate_id: TaskId) -> OSEvent:
    """An OS-initiated event, which needs no Actor row to exist (ADR-006 6.8)."""
    return OSEvent(
        id=new_id(EventId),
        event_type=EventType.STATE_TRANSITION_ALLOWED,
        aggregate_type="Task",
        aggregate_id=aggregate_id,
        actor_role=SystemActor.OS,
        occurred_at=utc_now(),
    )


async def _append_and_emit(*, aggregate_id: TaskId, commit: bool) -> OSEvent:
    """Appends an event and queues its wake-up in one transaction."""
    async with unit_of_work() as uow:
        recorded = await uow.events.add(_event(aggregate_id=aggregate_id))
        await emit_for_event(uow.session, recorded)
        if commit:
            await uow.commit()
    return recorded


async def test_a_committed_event_wakes_a_listening_subscriber(migrated_database: None) -> None:
    """The wake-up arrives and the subscriber reads the durable stream."""
    _ = migrated_database
    collector = Collector()

    async with EventSubscriber(collector) as subscriber:
        subscriber.run_in_background()
        recorded = await _append_and_emit(aggregate_id=new_id(TaskId), commit=True)
        await collector.wait_for(1)

    assert [event.id for event in collector.received] == [recorded.id]
    assert collector.received[0].sequence_number == recorded.sequence_number


async def test_a_rolled_back_transaction_notifies_nobody(migrated_database: None) -> None:
    """Emission is welded to the commit, so uncommitted work is never announced.

    This is the test an after-commit emit would fail. PostgreSQL holds a
    `pg_notify` until commit and discards it on rollback, which is precisely
    why ADR-006 6.2 moved the call inside the transaction.
    """
    _ = migrated_database
    collector = Collector()

    async with EventSubscriber(collector) as subscriber:
        subscriber.run_in_background()
        await _append_and_emit(aggregate_id=new_id(TaskId), commit=False)

        with pytest.raises(asyncio.TimeoutError):
            await collector.wait_for(1, timeout=QUIET_TIMEOUT)

    assert collector.received == []
    async with unit_of_work() as uow:
        assert await uow.events.latest_sequence_number() == 0


async def test_a_fresh_subscriber_starts_at_the_end_rather_than_replaying_history(
    migrated_database: None,
) -> None:
    """A restart begins from the current end of the stream (ADR-006 6.6)."""
    _ = migrated_database
    task_id = new_id(TaskId)
    existing = await _append_and_emit(aggregate_id=task_id, commit=True)

    collector = Collector()
    async with EventSubscriber(collector) as subscriber:
        assert subscriber.position == existing.sequence_number

    assert collector.received == []


async def test_a_subscriber_told_to_start_from_zero_replays_the_whole_stream(
    migrated_database: None,
) -> None:
    """The opening position is a choice, and the stream is durable either way."""
    _ = migrated_database
    task_id = new_id(TaskId)
    first = await _append_and_emit(aggregate_id=task_id, commit=True)
    second = await _append_and_emit(aggregate_id=task_id, commit=True)

    collector = Collector()
    async with EventSubscriber(collector, start_from=0):
        pass

    assert [event.id for event in collector.received] == [first.id, second.id]


async def test_events_appended_while_unheard_are_drained_in_order_on_return(
    migrated_database: None,
) -> None:
    """A missed wake-up is recoverable, which is what makes it only a wake-up.

    Nothing is listening while these events land. The subscriber's position —
    not the notification — decides what it processes and in what order.
    """
    _ = migrated_database
    task_id = new_id(TaskId)
    collector = Collector()

    async with EventSubscriber(collector) as subscriber:
        assert subscriber.position == 0

        missed = [await _append_and_emit(aggregate_id=task_id, commit=True) for _ in range(4)]

        delivered = await subscriber.drain()

    assert delivered == 4
    assert [event.id for event in collector.received] == [event.id for event in missed]
    assert subscriber.position == missed[-1].sequence_number


async def test_a_drain_reads_a_long_backlog_in_order_across_several_passes(
    migrated_database: None,
) -> None:
    """A bounded pass keeps a large backlog from arriving as one result set."""
    _ = migrated_database
    task_id = new_id(TaskId)
    collector = Collector()

    appended = [await _append_and_emit(aggregate_id=task_id, commit=True) for _ in range(7)]

    async with EventSubscriber(collector, start_from=0, batch_size=2) as subscriber:
        assert subscriber.position == appended[-1].sequence_number

    assert [event.id for event in collector.received] == [event.id for event in appended]


async def test_the_wake_up_carries_an_identifier_not_a_domain_object() -> None:
    """Receivers fetch authoritative state from PostgreSQL (Blueprint 14, item 3)."""
    event = _event(aggregate_id=new_id(TaskId))
    envelope = NotificationEnvelope.for_event(event)
    payload = envelope.to_payload()

    assert set(envelope.model_dump()) == {"event_id", "aggregate_type", "aggregate_id"}
    assert len(payload.encode("utf-8")) < NOTIFY_PAYLOAD_LIMIT_BYTES
    assert "payload" not in payload
    assert OS_EVENTS_CHANNEL == "os_events"
