"""The deterministic, synchronous Rule execution engine (ADR-004 4.2, 4.3).

The engine answers exactly one question:

    *Are the conditions this edge declares satisfied by these facts?*

It does **not** decide whether a transition is structurally defined — that is
the state machine's question — and it does not mutate, audit, or publish, which
belong to the Checkpoint 6 Kernel. Keeping the three separate keeps the
transactional boundary in exactly one place.

Evaluation is **hybrid**:

- Every rule whose declared prerequisites held is evaluated. Evaluation never
  stops at the first failure, so a requester receives one explicit missing list
  rather than one defect per reject-resubmit cycle.
- A rule is skipped **only** because a prerequisite it explicitly declared
  failed or was itself skipped. Skips cascade transitively.
- A prerequisite that was not requested for the edge under evaluation does not
  cause a skip: it did not fail, it was out of scope.

Order is fixed and owned by the OS: stage first, then position in the registry.
The engine exposes no way to add, remove, reorder, or prioritise a rule, and
``evaluate`` accepts only conditions and facts. Order is a property of the code,
never of any input.
"""

from collections.abc import Iterable, Sequence

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.errors import RuleContextIncompleteError, RuleDefinitionError
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleId
from ai_engineering_os.rules.context import RuleContext
from ai_engineering_os.rules.results import RuleEvaluation, RuleResult, RuleStatus

__all__ = ["RuleEngine", "evaluation_order"]

_BLOCKING_STATUSES: frozenset[RuleStatus] = frozenset({RuleStatus.FAILED, RuleStatus.SKIPPED})


def evaluation_order(rules: Sequence[Rule]) -> tuple[Rule, ...]:
    """Returns ``rules`` in the fixed OS evaluation order.

    Stage first, then declaration order inside the stage. Python's sort is
    stable, so declaration order is preserved exactly.
    """
    return tuple(sorted(rules, key=lambda rule: rule.stage))


def _validated(rules: Sequence[Rule]) -> tuple[Rule, ...]:
    """Returns the validated, ordered rule set, or raises ``RuleDefinitionError``.

    Validation is structural and happens once, when the engine is constructed —
    never during an evaluation. Requiring every prerequisite to sort strictly
    earlier than its dependent makes a cycle impossible to express, which is
    what keeps evaluation single-pass.
    """
    ordered = evaluation_order(rules)

    seen_ids: set[RuleId] = set()
    seen_conditions: set[TransitionCondition] = set()
    for rule in ordered:
        if rule.rule_id in seen_ids:
            raise RuleDefinitionError(f"Rule {rule.rule_id} is registered more than once")
        if rule.condition in seen_conditions:
            raise RuleDefinitionError(
                f"Condition {rule.condition} is evaluated by more than one registered rule"
            )
        seen_ids.add(rule.rule_id)
        seen_conditions.add(rule.condition)

    earlier: set[RuleId] = set()
    for rule in ordered:
        for prerequisite in sorted(rule.requires):
            if prerequisite not in seen_ids:
                raise RuleDefinitionError(
                    f"Rule {rule.rule_id} declares unknown prerequisite {prerequisite}"
                )
            if prerequisite not in earlier:
                raise RuleDefinitionError(
                    f"Rule {rule.rule_id} declares prerequisite {prerequisite}, which does not "
                    f"sort strictly earlier in the evaluation order"
                )
        earlier.add(rule.rule_id)

    return ordered


class RuleEngine:
    """Evaluates the rules registered for a set of requested conditions.

    The rule set is fixed when the engine is constructed. There is deliberately
    no ``add_rule``, ``remove_rule``, reorder, or runtime priority: an engine
    whose order can be influenced at runtime is an engine whose enforcement is
    not reproducible.
    """

    def __init__(self, rules: Sequence[Rule]) -> None:
        self._rules: tuple[Rule, ...] = _validated(rules)
        self._by_condition: dict[TransitionCondition, Rule] = {
            rule.condition: rule for rule in self._rules
        }

    @property
    def rules(self) -> tuple[Rule, ...]:
        """Every registered rule, in fixed evaluation order."""
        return self._rules

    @property
    def evaluated_conditions(self) -> frozenset[TransitionCondition]:
        """Every condition a registered rule evaluates."""
        return frozenset(self._by_condition)

    def rule_for(self, condition: TransitionCondition) -> Rule | None:
        """Returns the rule registered for ``condition``, if one exists."""
        return self._by_condition.get(condition)

    def evaluate(
        self,
        conditions: Iterable[TransitionCondition],
        context: RuleContext,
    ) -> RuleEvaluation:
        """Evaluates ``conditions`` against ``context`` and aggregates the outcome.

        The context is never mutated and no I/O is performed.

        Raises:
            RuleContextIncompleteError: if a selected rule requires a fact the
                context does not supply. The engine fails closed rather than
                letting a rule pass because the caller forgot a fact.
        """
        requested_set = set(conditions)
        requested = tuple(sorted(requested_set))
        selected = tuple(rule for rule in self._rules if rule.condition in requested_set)
        unevaluated = tuple(
            condition for condition in requested if condition not in self._by_condition
        )

        self._verify_facts_are_supplied(selected, context)

        statuses: dict[RuleId, RuleStatus] = {}
        results: list[RuleResult] = []
        for rule in selected:
            blocking = tuple(
                sorted(
                    prerequisite
                    for prerequisite in rule.requires
                    if statuses.get(prerequisite) in _BLOCKING_STATUSES
                )
            )
            if blocking:
                result = RuleResult(
                    rule_id=rule.rule_id,
                    condition=rule.condition,
                    status=RuleStatus.SKIPPED,
                    message=(
                        f"Not evaluated: prerequisite "
                        f"{', '.join(str(r) for r in blocking)} was not satisfied"
                    ),
                    skipped_because=blocking,
                )
            else:
                result = self._checked(rule, rule.evaluate(context))
            statuses[rule.rule_id] = result.status
            results.append(result)

        return RuleEvaluation(
            requested_conditions=requested,
            results=tuple(results),
            unevaluated_conditions=unevaluated,
        )

    def _verify_facts_are_supplied(self, selected: Sequence[Rule], context: RuleContext) -> None:
        """Fails closed before any rule runs when a required fact is absent.

        Checking every selected rule up front — rather than lazily as each rule
        is reached — keeps the outcome independent of which rule happens to fail
        first, so an incomplete context is reported the same way every time.
        """
        for rule in selected:
            missing = context.missing(rule.required_facts)
            if missing:
                names = tuple(fact.value for fact in missing)
                raise RuleContextIncompleteError(
                    f"Rule {rule.rule_id} requires facts the context does not supply: "
                    f"{', '.join(names)}",
                    rule_id=str(rule.rule_id),
                    missing_facts=names,
                )

    @staticmethod
    def _checked(rule: Rule, result: RuleResult) -> RuleResult:
        """Verifies a rule attributed its result to itself."""
        if result.rule_id != rule.rule_id or result.condition != rule.condition:
            raise RuleDefinitionError(
                f"Rule {rule.rule_id} returned a result attributed to "
                f"{result.rule_id} / {result.condition}"
            )
        return result
