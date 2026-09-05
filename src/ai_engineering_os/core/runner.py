"""The transactional Transition Runner (Blueprint 7.2, 15 Checkpoint 6).

**The core invariant this module exists to guarantee:**

    Rejected transition = no target-state mutation + durable rejection record.

The strategy is **Validation-First**. Everything is evaluated before anything is
mutated, so a refusal cannot roll back the record of itself. That ordering is
the whole design, and it is expressed here as one method rather than as a
sequence a caller assembles, because a caller assembling it could get the order
wrong exactly once and lose a rejection.

**What runs, in order, inside one transaction:**

1. The **state machine** answers *is this transition defined, and may this
   initiator request it?*
2. The **Rule Engine** answers *are the conditions this edge declares satisfied
   by these facts?* It runs only when step 1 allowed the transition — evaluating
   an edge's conditions when the edge does not exist would produce findings
   about a transition nobody can make.
3. On refusal: **nothing is mutated.** A ``REJECTED`` audit record and a
   ``StateTransitionRejected`` event are appended, the notification is emitted,
   and the transaction **commits** — the rejection is the outcome being made
   durable.
4. On success: the caller's mutation is applied, an ``ALLOWED`` audit record and
   the success event are appended, the notification is emitted, and the
   transaction commits.

**The Kernel calls the emitter itself** (ADR-006 6.9). Staging an event and
emitting its wake-up are two separate calls and are *not* enforced by
construction, so they are performed together here, in one place, and nowhere
else in the Kernel. The emit runs **inside** the committing transaction
(ADR-006 6.2), so a committed transition is never left unannounced.

**The runner commits.** ADR-005 5.5 places the transaction boundary in this
layer, and the invariant above depends on the rejection path committing. Leaving
that to the caller would make the guarantee conditional on every caller
remembering it.
"""

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from ai_engineering_os.domain.enums import Initiator, SystemActor
from ai_engineering_os.domain.event import (
    EventType,
    OSEvent,
    TransitionAuditRecord,
    TransitionOutcome,
)
from ai_engineering_os.domain.identifiers import ActorId, EventId, TransitionAuditId, new_id
from ai_engineering_os.events.bus import emit_for_event
from ai_engineering_os.rules.context import RuleContext
from ai_engineering_os.rules.registry import RULE_ENGINE
from ai_engineering_os.rules.results import RuleEvaluation, RuleStatus
from ai_engineering_os.state.machine import StateMachine, TransitionEvaluation
from ai_engineering_os.storage.unit_of_work import UnitOfWork

__all__ = ["TransitionRequest", "TransitionResult", "TransitionRunner"]

Mutation = Callable[[], Awaitable[None]]
"""The caller's state change, applied only after validation has passed."""


@dataclass(frozen=True, slots=True)
class TransitionRequest[StateT: StrEnum]:
    """One requested transition, with everything needed to evaluate it.

    Attributes:
        machine: The lifecycle graph governing the entity.
        entity_type: The entity's name, as recorded in the audit ledger.
        entity_id: The entity the transition applies to.
        from_state: The state the entity is in now.
        to_state: The state being requested.
        initiator: The role — or ``SystemActor.OS`` — requesting the transition.
        initiator_id: The requesting Actor, or ``None`` when the OS itself is
            the initiator. The OS is infrastructure and has no row in ``actors``
            (ADR-006 6.8).
        context: The facts the Rule Engine evaluates against.
        apply: The mutation to perform **only** if validation passes.
        allowed_event_type: The event appended on success. Defaults to
            ``STATE_TRANSITION_ALLOWED``; a caller may name a more specific
            domain event for the same transition.
        payload: Extra detail recorded on the event.
    """

    machine: StateMachine[StateT]
    entity_type: str
    entity_id: UUID
    from_state: StateT
    to_state: StateT
    initiator: Initiator
    initiator_id: ActorId | None
    context: RuleContext
    apply: Mutation
    allowed_event_type: EventType = EventType.STATE_TRANSITION_ALLOWED
    payload: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TransitionResult:
    """The complete, durable outcome of one evaluated transition.

    Both evaluations are returned whether or not the transition succeeded, so a
    caller can report precisely what refused it. ``rules`` is ``None`` only when
    the state machine refused first and the Rule Engine was never asked.
    """

    is_allowed: bool
    transition: TransitionEvaluation[Any]
    rules: RuleEvaluation | None
    audit: TransitionAuditRecord
    event: OSEvent

    @property
    def rejection_reasons(self) -> tuple[Mapping[str, Any], ...]:
        """The structured reasons a refusal was recorded with."""
        return self.audit.reasons


class TransitionRunner:
    """Evaluates, records, and — only if permitted — applies one transition."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def run[StateT: StrEnum](self, request: TransitionRequest[StateT]) -> TransitionResult:
        """Runs one transition to a durable outcome and commits.

        Raises:
            PersistenceError: if the transaction cannot be committed.
            ConcurrencyConflictError: if the entity changed since it was read.

        Neither is caught here. A transition whose commit failed has no durable
        outcome, and reporting one would be a lie.
        """
        transition = request.machine.evaluate(
            request.from_state, request.to_state, request.initiator
        )

        rules: RuleEvaluation | None = None
        if transition.is_allowed:
            rules = RULE_ENGINE.evaluate(transition.required_conditions, request.context)

        if not transition.is_allowed or (rules is not None and not rules.is_satisfied):
            return await self._refuse(request, transition, rules)

        # Validation has passed. Only now is anything mutated.
        await request.apply()
        return await self._allow(request, transition, rules)

    async def _refuse[StateT: StrEnum](
        self,
        request: TransitionRequest[StateT],
        transition: TransitionEvaluation[StateT],
        rules: RuleEvaluation | None,
    ) -> TransitionResult:
        """Records the refusal durably. The entity is left exactly as it was."""
        reasons = _reasons(transition, rules)
        audit = await self._append_audit(request, TransitionOutcome.REJECTED, reasons)
        event = await self._append_event(
            request,
            EventType.STATE_TRANSITION_REJECTED,
            {"outcome": TransitionOutcome.REJECTED.value, "reasons": list(reasons)},
        )
        await self._uow.commit()
        return TransitionResult(
            is_allowed=False, transition=transition, rules=rules, audit=audit, event=event
        )

    async def _allow[StateT: StrEnum](
        self,
        request: TransitionRequest[StateT],
        transition: TransitionEvaluation[StateT],
        rules: RuleEvaluation | None,
    ) -> TransitionResult:
        """Records the successful transition and commits the mutation with it."""
        audit = await self._append_audit(request, TransitionOutcome.ALLOWED, ())
        event = await self._append_event(
            request,
            request.allowed_event_type,
            {"outcome": TransitionOutcome.ALLOWED.value},
        )
        await self._uow.commit()
        return TransitionResult(
            is_allowed=True, transition=transition, rules=rules, audit=audit, event=event
        )

    async def _append_audit[StateT: StrEnum](
        self,
        request: TransitionRequest[StateT],
        outcome: TransitionOutcome,
        reasons: tuple[Mapping[str, Any], ...],
    ) -> TransitionAuditRecord:
        """Appends one line to the enforcement ledger (ADR-006 6.3)."""
        return await self._uow.transition_audit.add(
            TransitionAuditRecord(
                id=new_id(TransitionAuditId),
                entity_type=request.entity_type,
                entity_id=request.entity_id,
                from_state=str(request.from_state),
                attempted_state=str(request.to_state),
                outcome=outcome,
                requested_by=request.initiator_id,
                requested_by_role=request.initiator,
                reasons=reasons,
            )
        )

    async def _append_event[StateT: StrEnum](
        self,
        request: TransitionRequest[StateT],
        event_type: EventType,
        detail: Mapping[str, Any],
    ) -> OSEvent:
        """Appends the event **and emits its wake-up** (ADR-006 6.9).

        The two calls are here together because nothing else enforces that they
        happen together. The payload carries the transition and the caller's
        extra detail; it is **not** a per-event-type schema, which ADR-006 6.5
        deferred and ADR-007 leaves deferred.
        """
        payload: dict[str, Any] = {
            "from_state": str(request.from_state),
            "to_state": str(request.to_state),
            **detail,
            **(request.payload or {}),
        }
        event = await self._uow.events.add(
            OSEvent(
                id=new_id(EventId),
                event_type=event_type,
                aggregate_type=request.entity_type,
                aggregate_id=request.entity_id,
                actor_id=request.initiator_id,
                actor_role=request.initiator,
                payload=payload,
            )
        )
        await emit_for_event(self._uow.session, event)
        return event


def _reasons(
    transition: TransitionEvaluation[Any], rules: RuleEvaluation | None
) -> tuple[Mapping[str, Any], ...]:
    """Builds the structured refusal reasons recorded in the audit ledger.

    A refusal without a recorded reason leaves the requester unable to learn
    what to fix, so this never returns empty for a refused transition: the state
    machine refuses with rejections, and the Rule Engine refuses with failed or
    skipped results.
    """
    reasons: list[Mapping[str, Any]] = [
        {
            "source": "state_machine",
            "code": rejection.code.value,
            "message": rejection.message,
        }
        for rejection in transition.rejections
    ]
    if rules is not None:
        reasons.extend(_rule_reasons(rules))
    return tuple(reasons)


def _rule_reasons(rules: RuleEvaluation) -> Iterable[Mapping[str, Any]]:
    """Renders every unsatisfied rule result as a structured reason."""
    for result in rules.results:
        if result.status is RuleStatus.PASSED:
            continue
        yield {
            "source": "rule_engine",
            "rule_id": str(result.rule_id),
            "condition": str(result.condition),
            "status": str(result.status),
            "code": result.code.value if result.code is not None else None,
            "message": result.message,
        }


def initiator_id_for(initiator: Initiator, actor_id: ActorId | None) -> ActorId | None:
    """Returns the Actor id an audit record may carry for ``initiator``.

    The OS is infrastructure and has no row in ``actors``, so recording a person
    for a transition it initiated would be false (ADR-006 6.8). This drops an id
    supplied alongside ``SystemActor.OS`` rather than letting the domain model
    raise on it, so a caller that passes both gets the correct record instead of
    an error about a distinction it should not have to know.
    """
    return None if initiator is SystemActor.OS else actor_id
