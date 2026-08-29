"""Structured domain-level errors for AI Engineering OS.

These errors are pure domain signals. They intentionally carry no HTTP status
codes, transport concerns, or persistence concerns.
"""

from typing import ClassVar

__all__ = [
    "DomainError",
    "ImmutableRecordError",
    "InvariantViolationError",
    "RevisionSequenceError",
    "RuleContextIncompleteError",
    "RuleDefinitionError",
    "StateMachineDefinitionError",
]


class DomainError(Exception):
    """Base class for every deterministic AI Engineering OS domain failure."""

    code: ClassVar[str] = "DOMAIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class InvariantViolationError(DomainError):
    """Raised when a domain invariant is violated by an explicit operation."""

    code: ClassVar[str] = "INVARIANT_VIOLATION"


class ImmutableRecordError(DomainError):
    """Raised when an actor attempts to mutate a record the OS preserves immutably."""

    code: ClassVar[str] = "IMMUTABLE_RECORD"

    def __init__(self, message: str, *, record_type: str, operation: str) -> None:
        super().__init__(message)
        self.record_type = record_type
        self.operation = operation


class RevisionSequenceError(DomainError):
    """Raised when revision history would stop being strictly additive."""

    code: ClassVar[str] = "REVISION_SEQUENCE"

    def __init__(
        self,
        message: str,
        *,
        expected_revision_number: int,
        received_revision_number: int,
    ) -> None:
        super().__init__(message)
        self.expected_revision_number = expected_revision_number
        self.received_revision_number = received_revision_number


class StateMachineDefinitionError(DomainError):
    """Raised when a state machine is declared with an inconsistent transition graph."""

    code: ClassVar[str] = "STATE_MACHINE_DEFINITION"


class RuleDefinitionError(DomainError):
    """Raised when a rule set is declared with an inconsistent contract.

    Duplicate identifiers, duplicate conditions, an unknown prerequisite, or a
    prerequisite that does not sort strictly earlier than its dependent are all
    definition errors, detected when the registry is constructed rather than
    during an evaluation.
    """

    code: ClassVar[str] = "RULE_DEFINITION"


class RuleContextIncompleteError(DomainError):
    """Raised when the supplied facts do not cover what a rule requires.

    The Rule Engine fails closed: a rule never passes because the caller forgot
    to supply a fact (ADR-004 4.4).
    """

    code: ClassVar[str] = "RULE_CONTEXT_INCOMPLETE"

    def __init__(self, message: str, *, rule_id: str, missing_facts: tuple[str, ...]) -> None:
        super().__init__(message)
        self.rule_id = rule_id
        self.missing_facts = missing_facts
