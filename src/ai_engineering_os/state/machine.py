"""Deterministic lifecycle state machine primitives.

This module provides the domain-level transition definitions and evaluator that
the OS Kernel (Checkpoint 6) and Rule Engine (Checkpoint 3) will consume. It
contains no persistence, no HTTP, and no transport status codes.

An evaluation answers exactly four questions:

1. What is the current state?
2. What is the requested next state?
3. Is the transition valid?
4. If not, why was it rejected?
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import Initiator
from ai_engineering_os.domain.errors import DomainError, StateMachineDefinitionError

__all__ = [
    "StateMachine",
    "TransitionCondition",
    "TransitionDefinition",
    "TransitionEvaluation",
    "TransitionRejectedError",
    "TransitionRejection",
    "TransitionRejectionCode",
]


class TransitionRejectionCode(StrEnum):
    """Structured reasons a lifecycle transition is rejected at the domain level."""

    TERMINAL_STATE = "TERMINAL_STATE"
    UNDEFINED_TRANSITION = "UNDEFINED_TRANSITION"
    UNAUTHORIZED_INITIATOR = "UNAUTHORIZED_INITIATOR"


# The condition vocabulary is owned by the domain layer (ADR-004 4.7).
# ``TransitionCondition`` is re-exported here so existing imports from
# ``ai_engineering_os.state`` continue to resolve. The state layer *declares*
# which conditions govern each edge; the rules layer evaluates them.


@dataclass(frozen=True, slots=True)
class TransitionRejection:
    """A structured, testable explanation of why a transition was rejected."""

    code: TransitionRejectionCode
    entity: str
    from_state: str
    to_state: str
    message: str
    allowed_targets: tuple[str, ...] = ()
    allowed_initiators: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TransitionDefinition[StateT: StrEnum]:
    """One explicitly permitted edge in a lifecycle graph."""

    from_state: StateT
    to_state: StateT
    allowed_initiators: frozenset[Initiator]
    required_conditions: frozenset[TransitionCondition] = field(default_factory=frozenset)

    @property
    def key(self) -> tuple[StateT, StateT]:
        """The ``(from_state, to_state)`` pair identifying this transition."""
        return (self.from_state, self.to_state)


@dataclass(frozen=True, slots=True)
class TransitionEvaluation[StateT: StrEnum]:
    """The deterministic outcome of evaluating a requested transition."""

    entity: str
    from_state: StateT
    to_state: StateT
    initiator: Initiator
    is_allowed: bool
    rejections: tuple[TransitionRejection, ...] = ()
    required_conditions: frozenset[TransitionCondition] = field(default_factory=frozenset)

    @property
    def rejection_codes(self) -> tuple[TransitionRejectionCode, ...]:
        """The structured codes explaining a rejection."""
        return tuple(rejection.code for rejection in self.rejections)

    def raise_if_rejected(self) -> None:
        """Raises :class:`TransitionRejectedError` when the transition is invalid."""
        if not self.is_allowed:
            raise TransitionRejectedError(self)


class TransitionRejectedError(DomainError):
    """Raised when a rejected transition is surfaced as an exception."""

    code: ClassVar[str] = "TRANSITION_REJECTED"

    def __init__(self, evaluation: TransitionEvaluation[Any]) -> None:
        reasons = "; ".join(rejection.message for rejection in evaluation.rejections)
        super().__init__(
            f"{evaluation.entity} transition {evaluation.from_state} -> "
            f"{evaluation.to_state} rejected: {reasons}"
        )
        self.evaluation: TransitionEvaluation[Any] = evaluation


class StateMachine[StateT: StrEnum]:
    """A deterministic lifecycle graph with explicit, authority-aware transitions.

    Terminal states are derived rather than declared: a state is terminal when
    no transition out of it is explicitly defined.
    """

    def __init__(
        self,
        *,
        entity: str,
        state_type: type[StateT],
        initial_state: StateT,
        transitions: Sequence[TransitionDefinition[StateT]],
    ) -> None:
        self._entity = entity
        self._state_type = state_type
        self._initial_state = initial_state
        self._transitions: dict[tuple[StateT, StateT], TransitionDefinition[StateT]] = {}
        for transition in transitions:
            if transition.key in self._transitions:
                raise StateMachineDefinitionError(
                    f"{entity} declares transition {transition.from_state} -> "
                    f"{transition.to_state} more than once"
                )
            if transition.from_state == transition.to_state:
                raise StateMachineDefinitionError(
                    f"{entity} declares a self-transition on {transition.from_state}"
                )
            self._transitions[transition.key] = transition
        self._validate_states_are_declared()

    def _validate_states_are_declared(self) -> None:
        referenced = {state for key in self._transitions for state in key}
        undeclared = sorted(set(self._state_type) - referenced)
        if undeclared:
            raise StateMachineDefinitionError(
                f"{self._entity} declares states that no transition references: {undeclared}"
            )

    @property
    def entity(self) -> str:
        """The domain entity this lifecycle belongs to."""
        return self._entity

    @property
    def initial_state(self) -> StateT:
        """The state a newly created entity starts in."""
        return self._initial_state

    @property
    def states(self) -> frozenset[StateT]:
        """Every state in this lifecycle."""
        return frozenset(self._state_type)

    @property
    def transitions(self) -> tuple[TransitionDefinition[StateT], ...]:
        """Every explicitly permitted transition, in declaration order."""
        return tuple(self._transitions.values())

    @property
    def terminal_states(self) -> frozenset[StateT]:
        """States with no explicitly defined outgoing transition."""
        return frozenset(state for state in self._state_type if not self.allowed_targets(state))

    def is_terminal(self, state: StateT) -> bool:
        """Returns whether ``state`` has no defined outgoing transition."""
        return not self.allowed_targets(state)

    def allowed_targets(self, state: StateT) -> frozenset[StateT]:
        """Returns every state reachable from ``state`` in one transition."""
        return frozenset(
            to_state for (from_state, to_state) in self._transitions if from_state == state
        )

    def definition(
        self, from_state: StateT, to_state: StateT
    ) -> TransitionDefinition[StateT] | None:
        """Returns the transition definition for the given edge, if it exists."""
        return self._transitions.get((from_state, to_state))

    def allowed_initiators(self, from_state: StateT, to_state: StateT) -> frozenset[Initiator]:
        """Returns who may request the given transition."""
        transition = self.definition(from_state, to_state)
        return transition.allowed_initiators if transition else frozenset()

    def can_transition(self, from_state: StateT, to_state: StateT, initiator: Initiator) -> bool:
        """Returns whether the requested transition is valid for ``initiator``."""
        return self.evaluate(from_state, to_state, initiator).is_allowed

    def evaluate(
        self,
        from_state: StateT,
        to_state: StateT,
        initiator: Initiator,
    ) -> TransitionEvaluation[StateT]:
        """Deterministically evaluates a requested transition.

        A rejection never mutates anything: it returns a structured explanation
        that the OS enforcement layer records and returns to the requester.
        """
        if self.is_terminal(from_state):
            return self._rejected(
                from_state,
                to_state,
                initiator,
                TransitionRejection(
                    code=TransitionRejectionCode.TERMINAL_STATE,
                    entity=self._entity,
                    from_state=from_state,
                    to_state=to_state,
                    message=(
                        f"{self._entity} state {from_state} is terminal and defines no "
                        f"outgoing transition"
                    ),
                ),
            )

        transition = self.definition(from_state, to_state)
        if transition is None:
            return self._rejected(
                from_state,
                to_state,
                initiator,
                TransitionRejection(
                    code=TransitionRejectionCode.UNDEFINED_TRANSITION,
                    entity=self._entity,
                    from_state=from_state,
                    to_state=to_state,
                    message=(f"{self._entity} defines no transition {from_state} -> {to_state}"),
                    allowed_targets=_labels(self.allowed_targets(from_state)),
                ),
            )

        if initiator not in transition.allowed_initiators:
            return self._rejected(
                from_state,
                to_state,
                initiator,
                TransitionRejection(
                    code=TransitionRejectionCode.UNAUTHORIZED_INITIATOR,
                    entity=self._entity,
                    from_state=from_state,
                    to_state=to_state,
                    message=(
                        f"{initiator} may not request {self._entity} transition "
                        f"{from_state} -> {to_state}"
                    ),
                    allowed_initiators=_labels(transition.allowed_initiators),
                ),
            )

        return TransitionEvaluation(
            entity=self._entity,
            from_state=from_state,
            to_state=to_state,
            initiator=initiator,
            is_allowed=True,
            required_conditions=transition.required_conditions,
        )

    def _rejected(
        self,
        from_state: StateT,
        to_state: StateT,
        initiator: Initiator,
        rejection: TransitionRejection,
    ) -> TransitionEvaluation[StateT]:
        return TransitionEvaluation(
            entity=self._entity,
            from_state=from_state,
            to_state=to_state,
            initiator=initiator,
            is_allowed=False,
            rejections=(rejection,),
        )


def _labels(values: Iterable[StrEnum]) -> tuple[str, ...]:
    """Returns sorted string labels for a set of enum members."""
    return tuple(sorted(str(value) for value in values))
