"""The notification emitter (ADR-006 6.2, 6.7, 6.9).

**The emit runs inside the caller's transaction**, not after it commits.
PostgreSQL queues a ``pg_notify()`` and delivers it *only* if that transaction
commits, so the notification and the event it announces become atomic: a
committed transition is never left unannounced, and an uncommitted one is never
announced. This supersedes the Blueprint 7.2 step 7 post-commit emit.

**The emitter takes a session; it does not open one.** Placing this call inside
the event repository would make ``storage`` depend on ``events``, which already
depends on ``storage`` — the cycle Blueprint 2.2 exists to prevent. The
Checkpoint 6 Kernel sits above both, stages the event, and calls this (ADR-004
4.7, ADR-006 6.9).

**Nothing here commits.** The transaction owner decides that (ADR-005 5.5).
"""

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_engineering_os.domain.event import OSEvent
from ai_engineering_os.events.types import (
    NOTIFY_PAYLOAD_LIMIT_BYTES,
    OS_EVENTS_CHANNEL,
    NotificationEnvelope,
)
from ai_engineering_os.storage.errors import PersistenceError

__all__ = ["emit", "emit_for_event"]


async def emit(
    session: AsyncSession,
    envelope: NotificationEnvelope,
    *,
    channel: str = OS_EVENTS_CHANNEL,
) -> None:
    """Queues ``envelope`` for delivery when the caller's transaction commits.

    Raises:
        ValueError: if the payload exceeds PostgreSQL's ``NOTIFY`` limit. The
            envelope is small by construction, so this fires only if a caller
            has put something in it that does not belong there.
        PersistenceError: if the database rejects the call.
    """
    payload = envelope.to_payload()
    encoded = len(payload.encode("utf-8"))
    if encoded > NOTIFY_PAYLOAD_LIMIT_BYTES:
        raise ValueError(
            f"A notification payload of {encoded} bytes exceeds the "
            f"{NOTIFY_PAYLOAD_LIMIT_BYTES}-byte NOTIFY limit"
        )
    try:
        await session.execute(select(func.pg_notify(channel, payload)))
    except SQLAlchemyError as exc:
        raise PersistenceError(f"Emitting a notification on {channel} failed: {exc}") from exc


async def emit_for_event(
    session: AsyncSession,
    event: OSEvent,
    *,
    channel: str = OS_EVENTS_CHANNEL,
) -> None:
    """Queues the wake-up announcing ``event`` on the caller's transaction."""
    await emit(session, NotificationEnvelope.for_event(event), channel=channel)
