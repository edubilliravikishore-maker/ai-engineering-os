"""The asynchronous event subscriber (ADR-006 6.6, 6.7).

**A notification is only a wake-up. The work is always "read forward from my
position."** Every handler call originates from a read of ``os_events`` ordered
by ``sequence_number``, never from the contents of a notification. That single
choice delivers what ADR-002 claims for this layer: a lost, duplicated, or
out-of-order notification changes nothing, because the durable stream — not the
signal — decides what is processed and in what order.

**Subscription is established before the first drain.** ADR-006 6.6 requires
that no event be processed ahead of an older one still unread, and that is
preserved: nothing is handled until the initial drain completes. But the
``LISTEN`` itself is registered *first*, because an event committed between the
end of a drain and the start of a subscription would notify nobody and already
sit behind the position — a gap that would go unnoticed until the next
reconnect. Subscribing first closes it, and the position filter makes the
resulting duplicate wake-ups harmless.

**The position is held in memory** (ADR-006 6.6). On reconnect the subscriber
resumes from it and drains what it missed. On a full process restart it begins
from the current end of the stream. **This is a recorded limitation, not a
guarantee**: no event is lost, but events appended while this process was down
are not replayed to it.
"""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Self

import asyncpg

from ai_engineering_os.config import get_settings
from ai_engineering_os.domain.event import OSEvent
from ai_engineering_os.events.types import OS_EVENTS_CHANNEL
from ai_engineering_os.storage.unit_of_work import unit_of_work

__all__ = ["DEFAULT_BATCH_SIZE", "EventSubscriber", "listener_dsn"]

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 200
"""How many events one drain pass reads before looping.

A bounded pass keeps a long backlog from arriving as a single unbounded result
set; the position advances and the loop continues until the stream is exhausted.
"""

EventHandler = Callable[[OSEvent], Awaitable[None]]


def listener_dsn() -> str:
    """Returns the plain PostgreSQL DSN for a raw ``asyncpg`` connection.

    ``LISTEN`` needs a dedicated connection outside the SQLAlchemy pool: a
    pooled connection can be handed to someone else between notifications, and
    a subscription would silently stop being delivered.
    """
    return get_settings().async_database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _recorded_sequence(event: OSEvent) -> int:
    """Returns the sequence number of an event read back from the stream."""
    if event.sequence_number is None:
        raise ValueError(f"Event {event.id} was read from the stream without a sequence number")
    return event.sequence_number


class EventSubscriber:
    """Wakes on a notification and processes the durable stream in append order."""

    def __init__(
        self,
        handler: EventHandler,
        *,
        channel: str = OS_EVENTS_CHANNEL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        start_from: int | None = None,
    ) -> None:
        """Binds ``handler`` to ``channel``.

        ``start_from`` overrides the opening position. Left unset, the
        subscriber begins at the current end of the stream and waits for what
        happens next; passing ``0`` replays everything recorded so far.
        """
        self._handler = handler
        self._channel = channel
        self._batch_size = batch_size
        self._position = start_from
        self._wakeup = asyncio.Event()
        self._connection: asyncpg.Connection[Any] | None = None
        self._pump: asyncio.Task[None] | None = None

    @property
    def position(self) -> int:
        """The highest sequence number this subscriber has processed."""
        return self._position or 0

    @property
    def is_listening(self) -> bool:
        """Whether a live subscription is currently registered."""
        return self._connection is not None and not self._connection.is_closed()

    async def start(self) -> None:
        """Subscribes, establishes the opening position, and drains the backlog."""
        await self._subscribe()
        if self._position is None:
            async with unit_of_work() as uow:
                self._position = await uow.events.latest_sequence_number()
        await self.drain()

    async def stop(self) -> None:
        """Cancels the pump and closes the dedicated connection."""
        if self._pump is not None:
            self._pump.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pump
            self._pump = None
        await self._unsubscribe()

    async def drain(self) -> int:
        """Processes every event after the current position. Returns how many.

        Reads in bounded passes and advances the position after **each** handled
        event, so an interrupted drain resumes exactly where it stopped rather
        than replaying the batch.
        """
        delivered = 0
        while True:
            async with unit_of_work() as uow:
                batch = await uow.events.list_since(self.position, limit=self._batch_size)
            if not batch:
                return delivered
            for event in batch:
                await self._handler(event)
                self._position = _recorded_sequence(event)
                delivered += 1
            if len(batch) < self._batch_size:
                return delivered

    async def run_forever(self) -> None:
        """Waits for wake-ups and drains on each, reconnecting if the link drops."""
        while True:
            try:
                await self._wakeup.wait()
                self._wakeup.clear()
                await self.drain()
            except asyncio.CancelledError:
                raise
            except (asyncpg.PostgresError, OSError) as exc:
                logger.warning("Event subscription lost, reconnecting: %s", exc)
                await self._reconnect()

    def run_in_background(self) -> asyncio.Task[None]:
        """Starts :meth:`run_forever` as a task and returns it."""
        self._pump = asyncio.create_task(self.run_forever())
        return self._pump

    async def _reconnect(self) -> None:
        """Re-establishes the subscription and drains whatever was missed."""
        await self._unsubscribe()
        await self._subscribe()
        await self.drain()

    async def _subscribe(self) -> None:
        """Opens the dedicated connection and registers the ``LISTEN``."""
        self._connection = await asyncpg.connect(listener_dsn())
        await self._connection.add_listener(self._channel, self._on_notification)

    async def _unsubscribe(self) -> None:
        """Closes the dedicated connection if one is open."""
        if self._connection is None:
            return
        with contextlib.suppress(asyncpg.PostgresError, OSError):
            if not self._connection.is_closed():
                await self._connection.remove_listener(self._channel, self._on_notification)
                await self._connection.close()
        self._connection = None

    def _on_notification(self, *_: Any) -> None:
        """Records that something happened. The payload is deliberately ignored.

        Acting on the payload would make the notification authoritative, which
        ADR-002 forbids. The wake-up says "go look"; the stream says what.
        """
        self._wakeup.set()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()
