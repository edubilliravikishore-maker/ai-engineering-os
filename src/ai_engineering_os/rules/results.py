"""Structured rule outcomes (ADR-004 4.5).

A rule never returns a bare boolean and never returns a free-form string. It
returns a :class:`RuleResult` whose ``code`` is a stable machine identifier,
whose ``message`` explains the problem to a human, and whose ``details`` make
the failure actionable.

Result well-formedness is an enforced invariant rather than a convention:

======== ================================================
Status   Invariant
======== ================================================
PASSED   carries no code and no skip cause
FAILED   always carries a code and a message
SKIPPED  carries no code and always names its cause
======== ================================================

**A skip is never reported as a failure.**
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.errors import DomainError
from ai_engineering_os.rules.codes import RuleCode, RuleId

__all__ = [
    "RuleDetail",
    "RuleEvaluation",
    "RuleResult",
    "RuleStatus",
    "RulesRejectedError",
]


class RuleStatus(StrEnum):
    """The outcome of evaluating a single rule.

    ``NOT_APPLICABLE`` is deliberately absent (ADR-004 4.5). The engine
    evaluates only rules whose condition the state machine actually requested,
    so no rule can be inapplicable to an evaluation it was selected for, and a
    status with no producer is an unfalsifiable branch.
    """

    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True, slots=True)
class RuleDetail:
    """One typed, ordered piece of structured failure data.

    Values are ordered and immutable so a rejection renders identically on every
    evaluation of the same facts.
    """

    key: str
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("A rule detail must carry a non-empty key")
        if not isinstance(self.values, tuple):
            raise TypeError(f"Rule detail {self.key!r} values must be an immutable tuple")

    @classmethod
    def of(cls, key: str, values: Iterable[object]) -> "RuleDetail":
        """Builds a detail from any iterable, rendering each value as text."""
        return cls(key=key, values=tuple(str(value) for value in values))


@dataclass(frozen=True, slots=True)
class RuleResult:
    """The structured outcome of one rule against one context."""

    rule_id: RuleId
    condition: TransitionCondition
    status: RuleStatus
    code: RuleCode | None = None
    message: str = ""
    details: tuple[RuleDetail, ...] = ()
    skipped_because: tuple[RuleId, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.details, tuple):
            raise TypeError("RuleResult details must be an immutable tuple")
        if not isinstance(self.skipped_because, tuple):
            raise TypeError("RuleResult skipped_because must be an immutable tuple")
        if self.status is RuleStatus.PASSED and self.code is not None:
            raise ValueError("A PASSED rule result cannot carry a failure code")
        if self.status is RuleStatus.FAILED and self.code is None:
            raise ValueError("A FAILED rule result must carry a failure code")
        if self.status is RuleStatus.FAILED and not self.message:
            raise ValueError("A FAILED rule result must explain the failure")
        if self.status is RuleStatus.SKIPPED and self.code is not None:
            raise ValueError("A SKIPPED rule result cannot carry a failure code")
        if self.status is RuleStatus.SKIPPED and not self.skipped_because:
            raise ValueError("A SKIPPED rule result must name the prerequisites that caused it")
        if self.status is not RuleStatus.SKIPPED and self.skipped_because:
            raise ValueError("Only a SKIPPED rule result may name a skip cause")

    @property
    def is_failure(self) -> bool:
        """Returns whether this result is a meaningful failure."""
        return self.status is RuleStatus.FAILED

    def detail(self, key: str) -> tuple[str, ...]:
        """Returns the ordered values recorded under ``key``, or an empty tuple."""
        return next((d.values for d in self.details if d.key == key), ())


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    """The aggregate outcome of evaluating the conditions declared by one edge.

    ``unevaluated_conditions`` names conditions that were requested but have no
    registered rule. A gap in enforcement is therefore visible **in** the result
    rather than absent from it (ADR-004 4.5). It is reported, not silently
    treated as satisfied and not reported as a failure: a missing rule is an OS
    gap, not a requester's defect. Whether the OS may operate with such a gap is
    the Checkpoint 6 safety gate (ADR-004 4.12), not a runtime question.
    """

    requested_conditions: tuple[TransitionCondition, ...] = ()
    results: tuple[RuleResult, ...] = ()
    unevaluated_conditions: tuple[TransitionCondition, ...] = ()

    def __post_init__(self) -> None:
        for name, value in (
            ("requested_conditions", self.requested_conditions),
            ("results", self.results),
            ("unevaluated_conditions", self.unevaluated_conditions),
        ):
            if not isinstance(value, tuple):
                raise TypeError(f"RuleEvaluation {name} must be an immutable tuple")

    @property
    def is_satisfied(self) -> bool:
        """Returns whether every rule that ran was satisfied.

        This answers "did any evaluated rule reject?" — it deliberately does not
        answer "is every requested condition enforced?", which
        :attr:`has_unenforced_conditions` reports separately.
        """
        return not self.failures

    @property
    def has_unenforced_conditions(self) -> bool:
        """Returns whether a requested condition had no registered rule."""
        return bool(self.unevaluated_conditions)

    @property
    def failures(self) -> tuple[RuleResult, ...]:
        """Every meaningful failure, in evaluation order."""
        return tuple(r for r in self.results if r.status is RuleStatus.FAILED)

    @property
    def skipped(self) -> tuple[RuleResult, ...]:
        """Every rule skipped because a declared prerequisite failed or was skipped."""
        return tuple(r for r in self.results if r.status is RuleStatus.SKIPPED)

    @property
    def passed(self) -> tuple[RuleResult, ...]:
        """Every satisfied rule, in evaluation order."""
        return tuple(r for r in self.results if r.status is RuleStatus.PASSED)

    @property
    def failure_codes(self) -> tuple[RuleCode, ...]:
        """The stable failure codes explaining a rejection, in evaluation order."""
        return tuple(r.code for r in self.failures if r.code is not None)

    def result_for(self, rule_id: RuleId) -> RuleResult | None:
        """Returns the result produced by ``rule_id``, if that rule was selected."""
        return next((r for r in self.results if r.rule_id == rule_id), None)

    def raise_if_rejected(self) -> None:
        """Raises :class:`RulesRejectedError` when any evaluated rule failed."""
        if not self.is_satisfied:
            raise RulesRejectedError(self)


class RulesRejectedError(DomainError):
    """Raised when a rejected rule evaluation is surfaced as an exception.

    Mirrors the state layer's ``TransitionRejectedError``: the structured
    evaluation remains attached, so nothing is reduced to a string.
    """

    code: ClassVar[str] = "RULES_REJECTED"

    def __init__(self, evaluation: RuleEvaluation) -> None:
        reasons = "; ".join(f"{r.code}: {r.message}" for r in evaluation.failures)
        super().__init__(f"Rule evaluation rejected: {reasons}")
        self.evaluation = evaluation
