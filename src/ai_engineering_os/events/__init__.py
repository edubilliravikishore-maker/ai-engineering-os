"""Event announcement and the notification bus (Blueprint 2.2, 11; ADR-006).

This package announces what ``storage`` has recorded. It holds the notification
envelope, the single channel, the emitter, and the subscriber.

**It does not hold the event vocabulary.** ``EventType``, ``OSEvent``,
``TransitionOutcome``, and ``TransitionAuditRecord`` live in ``domain`` by the
ruling of ADR-006 6.11, so ``storage`` can persist them without importing this
package and inverting the Blueprint 2.2 dependency direction.

**Nothing here opens a transaction or commits one.** The emitter runs on the
session it is handed (ADR-005 5.5, ADR-006 6.9), and the Checkpoint 6 Kernel is
the component that will call it.
"""

from ai_engineering_os.events.bus import emit, emit_for_event
from ai_engineering_os.events.listener import DEFAULT_BATCH_SIZE, EventSubscriber, listener_dsn
from ai_engineering_os.events.types import (
    NOTIFY_PAYLOAD_LIMIT_BYTES,
    OS_EVENTS_CHANNEL,
    NotificationEnvelope,
)

__all__ = [
    "DEFAULT_BATCH_SIZE",
    "NOTIFY_PAYLOAD_LIMIT_BYTES",
    "OS_EVENTS_CHANNEL",
    "EventSubscriber",
    "NotificationEnvelope",
    "emit",
    "emit_for_event",
    "listener_dsn",
]
