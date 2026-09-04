"""Event store repository — append-only (ADR-005 5.8, ADR-006 6.1).

**There is no update method and no delete method.** An event that could be
rewritten would record nothing trustworthy, and the audit history the OS depends
on would be destructible through the persistence layer.

Every read here orders by ``sequence_number`` — never by ``occurred_at``, which
the domain supplies and which can tie or skew, and never by the persistence
metadata timestamps ADR-005 5.9 forbids for exactly this purpose.
"""

from uuid import UUID

from sqlalchemy import func, select

from ai_engineering_os.domain.event import OSEvent
from ai_engineering_os.domain.identifiers import EventId
from ai_engineering_os.storage.mappers.event import to_domain_event, to_event_row
from ai_engineering_os.storage.models.event import OSEventRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["EventRepository"]


class EventRepository(BaseRepository[OSEventRow]):
    """Appends and reads the immutable event stream."""

    row_type = OSEventRow
    entity_name = "OSEvent"

    async def add(self, event: OSEvent) -> OSEvent:
        """Appends ``event`` within the caller's transaction and returns it recorded.

        The returned object carries the ``sequence_number`` the database
        assigned, which the caller could not have supplied and which a
        subscriber resumes from (ADR-006 6.1, 6.6).
        """
        row = to_event_row(event)
        self._stage(row)
        await self._flush()
        return to_domain_event(row)

    async def get_by_id(self, event_id: EventId) -> OSEvent:
        """Returns the event recorded under ``event_id``."""
        return to_domain_event(await self._require_row(event_id))

    async def list_since(
        self, sequence_number: int, *, limit: int | None = None
    ) -> tuple[OSEvent, ...]:
        """Returns events appended after ``sequence_number``, in append order.

        This is the backlog drain of ADR-006 6.6. A subscriber calls it on
        connect and on every reconnect **before** it begins waiting on
        notifications, so a newer event is never processed ahead of an older one
        still unread.

        Passing ``0`` returns the whole stream from the beginning. ``limit``
        bounds a single drain so a long backlog is read in order across several
        calls rather than in one unbounded result set; the caller advances its
        position and calls again.
        """
        statement = (
            select(OSEventRow)
            .where(OSEventRow.sequence_number > sequence_number)
            .order_by(OSEventRow.sequence_number)
        )
        if limit is not None:
            statement = statement.limit(limit)
        with self._translating():
            result = await self._session.execute(statement)
        return tuple(to_domain_event(self._track(row)) for row in result.scalars().all())

    async def list_by_aggregate(self, aggregate_id: UUID) -> tuple[OSEvent, ...]:
        """Returns every event recorded against ``aggregate_id``, in append order."""
        rows = await self._rows_where(
            OSEventRow.aggregate_id == aggregate_id,
            order_by=OSEventRow.sequence_number,
        )
        return tuple(to_domain_event(row) for row in rows)

    async def latest_sequence_number(self) -> int:
        """Returns the highest sequence number appended, or ``0`` if the stream is empty.

        A subscriber starting fresh uses this as its opening position, so it
        waits for what happens next rather than replaying all of history
        (ADR-006 6.6).
        """
        statement = select(func.max(OSEventRow.sequence_number))
        with self._translating():
            result = await self._session.execute(statement)
        return result.scalar_one_or_none() or 0
