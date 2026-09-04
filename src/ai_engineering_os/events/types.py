"""The notification envelope and the channel it travels on (ADR-006 6.5, 6.7).

The event *vocabulary* is not here. ``EventType``, ``OSEvent``,
``TransitionOutcome``, and ``TransitionAuditRecord`` live in ``domain`` by the
ruling of ADR-006 6.11: ``storage`` persists them and ``events`` announces them,
and a vocabulary two sibling layers both consume belongs beneath both.

What is here is genuinely infrastructure: the thin payload a wake-up carries and
the single channel it travels on.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ai_engineering_os.domain.event import OSEvent

__all__ = ["NOTIFY_PAYLOAD_LIMIT_BYTES", "OS_EVENTS_CHANNEL", "NotificationEnvelope"]

OS_EVENTS_CHANNEL = "os_events"
"""The single channel every notification travels on (ADR-006 6.7).

Blueprint 7.2's ``task_events`` is replaced. Subscribers filter for what
concerns them; a second channel would mean a second reconnect-and-drain
implementation, which is the one piece of ordering-sensitive logic in this layer.
"""

NOTIFY_PAYLOAD_LIMIT_BYTES = 8000
"""PostgreSQL's hard limit on a ``NOTIFY`` payload (Blueprint 14, item 3)."""


class NotificationEnvelope(BaseModel):
    """The wake-up itself — an identifier, never a domain object.

    Receivers fetch authoritative state from PostgreSQL (Blueprint 14, item 3).
    Sending the event itself would put domain data in a channel that guarantees
    neither delivery nor durability, and would eventually exceed the payload
    limit.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: UUID
    aggregate_type: str
    aggregate_id: UUID

    @classmethod
    def for_event(cls, event: OSEvent) -> "NotificationEnvelope":
        """Builds the wake-up announcing ``event``."""
        return cls(
            event_id=event.id,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
        )

    def to_payload(self) -> str:
        """Returns the JSON payload carried by ``pg_notify``."""
        return self.model_dump_json()
