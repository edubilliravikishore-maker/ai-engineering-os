"""The single abstract Rule contract (ADR-004 4.1, 4.6).

A rule is an **explicit, strongly typed Python class**. There is deliberately no
JSON or YAML rule DSL, no configuration-driven rule language, no runtime
expression evaluator, and no LLM evaluation. Extensibility lives at the engine
boundary — adding a rule class — never in an invented rule programming language.

A rule **evaluates and returns**. It performs no other action: it mutates no
entity, writes no record, publishes no event, and performs no I/O. Mutation,
audit, and event publication belong to the Checkpoint 6 OS Kernel.

Rules are stateless. An instance holds no evaluation state, so the same instance
may be evaluated repeatedly and in any interleaving with identical results.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult, RuleStatus

__all__ = ["Rule"]


class Rule(ABC):
    """One deterministic, read-only OS validation requirement evaluator.

    Attributes:
        rule_id: Stable machine identifier of this rule.
        condition: The single named condition this rule evaluates.
        stage: The OS-owned evaluation stage this rule belongs to.
        required_facts: The context facts this rule reads. The engine verifies
            they are supplied **before** calling the rule and fails closed when
            they are not, so a rule never passes because a fact was missing.
        requires: Rules whose failure makes this rule's own verdict meaningless.
            "Meaningless" is always **declared** by the rule author; the engine
            never infers it.
    """

    rule_id: ClassVar[RuleId]
    condition: ClassVar[TransitionCondition]
    stage: ClassVar[RuleStage]
    required_facts: ClassVar[frozenset[RuleFact]]
    requires: ClassVar[frozenset[RuleId]] = frozenset()

    @abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns the structured outcome of this rule against ``context``.

        The implementation must be a pure function of ``context``: it reads
        facts and returns a result, and does nothing else.
        """

    def passed(self, message: str) -> RuleResult:
        """Builds a PASSED result attributed to this rule."""
        return RuleResult(
            rule_id=self.rule_id,
            condition=self.condition,
            status=RuleStatus.PASSED,
            message=message,
        )

    def failed(
        self,
        code: RuleCode,
        message: str,
        *details: RuleDetail,
    ) -> RuleResult:
        """Builds a FAILED result attributed to this rule."""
        return RuleResult(
            rule_id=self.rule_id,
            condition=self.condition,
            status=RuleStatus.FAILED,
            code=code,
            message=message,
            details=details,
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(rule_id={self.rule_id!r}, stage={self.stage!r})"
