"""Unit tests for the generic Rule Engine mechanics (ADR-004 4.2, 4.3, 4.4, 4.5).

These exercise the engine itself against purpose-built stub rules, so a failure
here is unambiguously an engine defect rather than a rule defect. The six real
OS rules are covered by ``test_rules.py``.
"""

from typing import Any

import pytest

from ai_engineering_os.domain import Actor, Feature, Task, TransitionCondition
from ai_engineering_os.domain.errors import RuleContextIncompleteError, RuleDefinitionError
from ai_engineering_os.rules import (
    Rule,
    RuleCode,
    RuleContext,
    RuleDetail,
    RuleEngine,
    RuleEvaluation,
    RuleFact,
    RuleId,
    RuleResult,
    RulesRejectedError,
    RuleStage,
    RuleStatus,
)

# --------------------------------------------------------------------------
# Stub rules
#
# Stubs reuse the real RuleId and TransitionCondition vocabularies because both
# are closed enumerations: the engine must be exercised with the identifiers it
# will actually receive, not with invented ones.
# --------------------------------------------------------------------------


class _StubRule(Rule):
    """A rule whose verdict is fixed at construction."""

    required_facts = frozenset()

    def __init__(self, *, outcome: bool = True) -> None:
        self._outcome = outcome

    def evaluate(self, context: RuleContext) -> RuleResult:  # noqa: ARG002
        if self._outcome:
            return self.passed(f"{self.rule_id} passed")
        return self.failed(
            RuleCode.TASK_NOT_ACCEPTED,
            f"{self.rule_id} failed",
            RuleDetail.of("stub", [self.rule_id]),
        )


class _AuthorityStub(_StubRule):
    rule_id = RuleId.WORKER_CAPABILITY_MATCHES
    condition = TransitionCondition.WORKER_CAPABILITY_MATCHES
    stage = RuleStage.ACTOR_AUTHORITY


class _DependencyStub(_StubRule):
    rule_id = RuleId.DEPENDENCIES_ACCEPTED
    condition = TransitionCondition.DEPENDENCIES_ACCEPTED
    stage = RuleStage.PLAN_DEPENDENCY


class _EvidenceStub(_StubRule):
    rule_id = RuleId.SYSTEM_EVIDENCE_REQUIRED
    condition = TransitionCondition.MANDATORY_SYSTEM_EVIDENCE_ATTACHED
    stage = RuleStage.EVIDENCE


class _AcceptanceStub(_StubRule):
    rule_id = RuleId.ALL_TASKS_ACCEPTED
    condition = TransitionCondition.ALL_TASKS_ACCEPTED
    stage = RuleStage.ACCEPTANCE


class _PrerequisiteStub(_StubRule):
    rule_id = RuleId.QA_FINAL_PASS_RECORDED
    condition = TransitionCondition.QA_FINAL_PASS_RECORDED
    stage = RuleStage.ACCEPTANCE


class _DependentStub(_StubRule):
    rule_id = RuleId.QA_IN_SCOPE_ZERO_DEFECTS
    condition = TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS
    stage = RuleStage.ACCEPTANCE
    requires = frozenset({RuleId.QA_FINAL_PASS_RECORDED})


class _TransitivelyDependentStub(_StubRule):
    rule_id = RuleId.ALL_TASKS_ACCEPTED
    condition = TransitionCondition.ALL_TASKS_ACCEPTED
    stage = RuleStage.ACCEPTANCE
    requires = frozenset({RuleId.QA_IN_SCOPE_ZERO_DEFECTS})


class _FactHungryStub(_StubRule):
    rule_id = RuleId.WORKER_CAPABILITY_MATCHES
    condition = TransitionCondition.WORKER_CAPABILITY_MATCHES
    stage = RuleStage.ACTOR_AUTHORITY
    required_facts = frozenset({RuleFact.CANDIDATE_WORKER, RuleFact.TASK})


class _MisattributedStub(_StubRule):
    rule_id = RuleId.WORKER_CAPABILITY_MATCHES
    condition = TransitionCondition.WORKER_CAPABILITY_MATCHES
    stage = RuleStage.ACTOR_AUTHORITY

    def evaluate(self, context: RuleContext) -> RuleResult:  # noqa: ARG002
        return RuleResult(
            rule_id=RuleId.ALL_TASKS_ACCEPTED,
            condition=TransitionCondition.ALL_TASKS_ACCEPTED,
            status=RuleStatus.PASSED,
        )


@pytest.fixture
def empty_context() -> RuleContext:
    """A context supplying no facts; stub rules require none."""
    return RuleContext()


# --------------------------------------------------------------------------
# Selection and reporting
# --------------------------------------------------------------------------


def test_an_empty_rule_set_evaluates_to_an_empty_result(empty_context: RuleContext) -> None:
    """Verifies an engine with no rules is constructible and reports the gap."""
    engine = RuleEngine(())
    evaluation = engine.evaluate([TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context)
    assert evaluation.results == ()
    assert evaluation.unevaluated_conditions == (TransitionCondition.WORKER_CAPABILITY_MATCHES,)
    assert evaluation.has_unenforced_conditions


def test_evaluating_no_conditions_returns_an_empty_evaluation(empty_context: RuleContext) -> None:
    """Verifies an edge declaring no condition is satisfied without any rule running."""
    evaluation = RuleEngine((_AuthorityStub(),)).evaluate((), empty_context)
    assert evaluation == RuleEvaluation()
    assert evaluation.is_satisfied


def test_a_requested_condition_with_no_rule_is_reported(empty_context: RuleContext) -> None:
    """Verifies an enforcement gap is visible in the result rather than absent from it."""
    engine = RuleEngine((_AuthorityStub(),))
    evaluation = engine.evaluate(
        [
            TransitionCondition.WORKER_CAPABILITY_MATCHES,
            TransitionCondition.WORKER_IS_ACTIVE,
            TransitionCondition.ORIGINATING_PLAN_ACTIVE,
        ],
        empty_context,
    )
    assert evaluation.unevaluated_conditions == (
        TransitionCondition.ORIGINATING_PLAN_ACTIVE,
        TransitionCondition.WORKER_IS_ACTIVE,
    )
    assert [r.rule_id for r in evaluation.results] == [RuleId.WORKER_CAPABILITY_MATCHES]


def test_an_unevaluated_condition_is_not_reported_as_a_failure(empty_context: RuleContext) -> None:
    """Verifies a missing rule is an OS gap, never blamed on the requester."""
    evaluation = RuleEngine(()).evaluate([TransitionCondition.WORKER_IS_ACTIVE], empty_context)
    assert evaluation.failures == ()
    assert evaluation.failure_codes == ()
    assert evaluation.is_satisfied
    assert evaluation.has_unenforced_conditions


def test_a_registered_rule_is_not_evaluated_unless_requested(empty_context: RuleContext) -> None:
    """Verifies the engine evaluates the requested edge, not the whole registry."""
    engine = RuleEngine((_AuthorityStub(outcome=False), _DependencyStub()))
    evaluation = engine.evaluate([TransitionCondition.DEPENDENCIES_ACCEPTED], empty_context)
    assert [r.rule_id for r in evaluation.results] == [RuleId.DEPENDENCIES_ACCEPTED]
    assert evaluation.is_satisfied


# --------------------------------------------------------------------------
# Pass, fail, and aggregation
# --------------------------------------------------------------------------


def test_a_single_passing_rule_is_satisfied(empty_context: RuleContext) -> None:
    """Verifies the simplest satisfied evaluation."""
    evaluation = RuleEngine((_AuthorityStub(),)).evaluate(
        [TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context
    )
    assert evaluation.is_satisfied
    assert evaluation.results[0].status is RuleStatus.PASSED
    assert evaluation.results[0].code is None


def test_a_single_failing_rule_rejects(empty_context: RuleContext) -> None:
    """Verifies one failure is enough to reject, with a stable code."""
    evaluation = RuleEngine((_AuthorityStub(outcome=False),)).evaluate(
        [TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context
    )
    assert not evaluation.is_satisfied
    assert evaluation.failure_codes == (RuleCode.TASK_NOT_ACCEPTED,)


def test_independent_failures_aggregate(empty_context: RuleContext) -> None:
    """Verifies evaluation never stops at the first failure (ADR-004 4.2).

    Stopping early would force a requester through one reject-resubmit cycle per
    defect, which is what the explicit-missing-list model exists to prevent.
    """
    engine = RuleEngine(
        (
            _AuthorityStub(outcome=False),
            _DependencyStub(outcome=False),
            _EvidenceStub(outcome=False),
        )
    )
    evaluation = engine.evaluate(
        [
            TransitionCondition.WORKER_CAPABILITY_MATCHES,
            TransitionCondition.DEPENDENCIES_ACCEPTED,
            TransitionCondition.MANDATORY_SYSTEM_EVIDENCE_ATTACHED,
        ],
        empty_context,
    )
    assert len(evaluation.failures) == 3
    assert [r.rule_id for r in evaluation.failures] == [
        RuleId.WORKER_CAPABILITY_MATCHES,
        RuleId.DEPENDENCIES_ACCEPTED,
        RuleId.SYSTEM_EVIDENCE_REQUIRED,
    ]


def test_multiple_rules_report_mixed_outcomes(empty_context: RuleContext) -> None:
    """Verifies a passing rule and a failing rule are both reported."""
    engine = RuleEngine((_AuthorityStub(), _DependencyStub(outcome=False)))
    evaluation = engine.evaluate(
        [
            TransitionCondition.WORKER_CAPABILITY_MATCHES,
            TransitionCondition.DEPENDENCIES_ACCEPTED,
        ],
        empty_context,
    )
    assert len(evaluation.passed) == 1
    assert len(evaluation.failures) == 1
    assert len(evaluation.results) == 2


# --------------------------------------------------------------------------
# Prerequisites and skipping
# --------------------------------------------------------------------------


def test_a_failed_prerequisite_skips_its_dependent(empty_context: RuleContext) -> None:
    """Verifies a dependent is skipped rather than producing a misleading verdict."""
    engine = RuleEngine((_PrerequisiteStub(outcome=False), _DependentStub(outcome=False)))
    evaluation = engine.evaluate(
        [
            TransitionCondition.QA_FINAL_PASS_RECORDED,
            TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS,
        ],
        empty_context,
    )
    dependent = evaluation.result_for(RuleId.QA_IN_SCOPE_ZERO_DEFECTS)
    assert dependent is not None
    assert dependent.status is RuleStatus.SKIPPED
    assert dependent.skipped_because == (RuleId.QA_FINAL_PASS_RECORDED,)
    assert dependent.code is None


def test_a_skip_is_never_reported_as_a_failure(empty_context: RuleContext) -> None:
    """Verifies the skipped dependent does not inflate the failure list."""
    engine = RuleEngine((_PrerequisiteStub(outcome=False), _DependentStub(outcome=False)))
    evaluation = engine.evaluate(
        [
            TransitionCondition.QA_FINAL_PASS_RECORDED,
            TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS,
        ],
        empty_context,
    )
    assert [r.rule_id for r in evaluation.failures] == [RuleId.QA_FINAL_PASS_RECORDED]
    assert [r.rule_id for r in evaluation.skipped] == [RuleId.QA_IN_SCOPE_ZERO_DEFECTS]


def test_skips_cascade_transitively(empty_context: RuleContext) -> None:
    """Verifies a skip caused by a skip is itself a skip (ADR-004 4.2)."""
    engine = RuleEngine(
        (
            _PrerequisiteStub(outcome=False),
            _DependentStub(),
            _TransitivelyDependentStub(),
        )
    )
    evaluation = engine.evaluate(
        [
            TransitionCondition.QA_FINAL_PASS_RECORDED,
            TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS,
            TransitionCondition.ALL_TASKS_ACCEPTED,
        ],
        empty_context,
    )
    transitive = evaluation.result_for(RuleId.ALL_TASKS_ACCEPTED)
    assert transitive is not None
    assert transitive.status is RuleStatus.SKIPPED
    assert transitive.skipped_because == (RuleId.QA_IN_SCOPE_ZERO_DEFECTS,)


def test_an_unrequested_prerequisite_does_not_cause_a_skip(empty_context: RuleContext) -> None:
    """Verifies out-of-scope is not failure (ADR-004 4.2).

    A prerequisite that was not requested for this edge did not fail; it simply
    was not part of the question being asked.
    """
    engine = RuleEngine((_PrerequisiteStub(outcome=False), _DependentStub()))
    evaluation = engine.evaluate(
        [TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS], empty_context
    )
    dependent = evaluation.result_for(RuleId.QA_IN_SCOPE_ZERO_DEFECTS)
    assert dependent is not None
    assert dependent.status is RuleStatus.PASSED


def test_independent_rules_still_run_when_another_rule_is_skipped(
    empty_context: RuleContext,
) -> None:
    """Verifies a skip never suppresses an unrelated rule."""
    engine = RuleEngine(
        (
            _AuthorityStub(outcome=False),
            _PrerequisiteStub(outcome=False),
            _DependentStub(),
        )
    )
    evaluation = engine.evaluate(
        [
            TransitionCondition.WORKER_CAPABILITY_MATCHES,
            TransitionCondition.QA_FINAL_PASS_RECORDED,
            TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS,
        ],
        empty_context,
    )
    assert len(evaluation.failures) == 2
    assert len(evaluation.skipped) == 1


# --------------------------------------------------------------------------
# Ordering
# --------------------------------------------------------------------------


def test_evaluation_order_is_stage_then_declaration(empty_context: RuleContext) -> None:
    """Verifies stage governs order regardless of registration order (ADR-004 4.3)."""
    engine = RuleEngine(
        (
            _AcceptanceStub(),
            _EvidenceStub(),
            _DependencyStub(),
            _AuthorityStub(),
        )
    )
    evaluation = engine.evaluate(
        [
            TransitionCondition.ALL_TASKS_ACCEPTED,
            TransitionCondition.MANDATORY_SYSTEM_EVIDENCE_ATTACHED,
            TransitionCondition.DEPENDENCIES_ACCEPTED,
            TransitionCondition.WORKER_CAPABILITY_MATCHES,
        ],
        empty_context,
    )
    assert [r.rule_id for r in evaluation.results] == [
        RuleId.WORKER_CAPABILITY_MATCHES,
        RuleId.DEPENDENCIES_ACCEPTED,
        RuleId.SYSTEM_EVIDENCE_REQUIRED,
        RuleId.ALL_TASKS_ACCEPTED,
    ]


def test_declaration_order_breaks_ties_inside_a_stage(empty_context: RuleContext) -> None:
    """Verifies registry position, not name or hash, orders rules within a stage."""
    engine = RuleEngine((_PrerequisiteStub(), _AcceptanceStub()))
    evaluation = engine.evaluate(
        [
            TransitionCondition.ALL_TASKS_ACCEPTED,
            TransitionCondition.QA_FINAL_PASS_RECORDED,
        ],
        empty_context,
    )
    assert [r.rule_id for r in evaluation.results] == [
        RuleId.QA_FINAL_PASS_RECORDED,
        RuleId.ALL_TASKS_ACCEPTED,
    ]


def test_the_requested_condition_order_does_not_change_the_result(
    empty_context: RuleContext,
) -> None:
    """Verifies input order cannot influence evaluation order."""
    engine = RuleEngine((_AuthorityStub(), _DependencyStub()))
    conditions = [
        TransitionCondition.WORKER_CAPABILITY_MATCHES,
        TransitionCondition.DEPENDENCIES_ACCEPTED,
    ]
    assert engine.evaluate(conditions, empty_context) == engine.evaluate(
        list(reversed(conditions)), empty_context
    )


def test_repeated_evaluation_is_deterministic(empty_context: RuleContext) -> None:
    """Verifies identical facts produce identical results (ADR-002 testing principles)."""
    engine = RuleEngine((_AuthorityStub(outcome=False), _DependencyStub(outcome=False)))
    conditions = [
        TransitionCondition.WORKER_CAPABILITY_MATCHES,
        TransitionCondition.DEPENDENCIES_ACCEPTED,
    ]
    first = engine.evaluate(conditions, empty_context)
    for _ in range(5):
        assert engine.evaluate(conditions, empty_context) == first


def test_the_engine_exposes_no_mutation_or_reordering_api() -> None:
    """Verifies order is a property of the code, never of any input (ADR-004 4.3)."""
    for forbidden in ("add_rule", "remove_rule", "reorder", "set_priority", "register"):
        assert not hasattr(RuleEngine, forbidden)


# --------------------------------------------------------------------------
# Registry validation
# --------------------------------------------------------------------------


def test_a_duplicate_rule_id_is_rejected() -> None:
    """Verifies one identifier can only ever mean one rule."""
    with pytest.raises(RuleDefinitionError, match="registered more than once"):
        RuleEngine((_AuthorityStub(), _AuthorityStub()))


def test_a_duplicate_condition_is_rejected() -> None:
    """Verifies a condition has exactly one evaluator, so no verdict can compete."""

    class _CompetingStub(_StubRule):
        rule_id = RuleId.DEPENDENCIES_ACCEPTED
        condition = TransitionCondition.WORKER_CAPABILITY_MATCHES
        stage = RuleStage.ACTOR_AUTHORITY

    with pytest.raises(RuleDefinitionError, match="more than one registered rule"):
        RuleEngine((_AuthorityStub(), _CompetingStub()))


def test_an_unknown_prerequisite_is_rejected() -> None:
    """Verifies a rule cannot declare a prerequisite that does not exist."""
    with pytest.raises(RuleDefinitionError, match="unknown prerequisite"):
        RuleEngine((_DependentStub(),))


def test_a_prerequisite_that_sorts_later_is_rejected() -> None:
    """Verifies a prerequisite must sort strictly earlier, keeping evaluation single-pass."""

    class _BackwardsDependentStub(_StubRule):
        rule_id = RuleId.WORKER_CAPABILITY_MATCHES
        condition = TransitionCondition.WORKER_CAPABILITY_MATCHES
        stage = RuleStage.ACTOR_AUTHORITY
        requires = frozenset({RuleId.ALL_TASKS_ACCEPTED})

    with pytest.raises(RuleDefinitionError, match="does not sort strictly earlier"):
        RuleEngine((_BackwardsDependentStub(), _AcceptanceStub()))


def test_a_same_stage_prerequisite_declared_later_is_rejected() -> None:
    """Verifies declaration order inside a stage is enforced, not just stage order."""
    with pytest.raises(RuleDefinitionError, match="does not sort strictly earlier"):
        RuleEngine((_DependentStub(), _PrerequisiteStub()))


def test_a_dependency_cycle_is_structurally_impossible() -> None:
    """Verifies a cycle cannot be registered (ADR-004 4.2).

    A cycle always contains an edge pointing at or after its dependent, so the
    strictly-earlier ordering constraint rejects it without a separate cycle
    search.
    """

    class _CycleA(_StubRule):
        rule_id = RuleId.QA_FINAL_PASS_RECORDED
        condition = TransitionCondition.QA_FINAL_PASS_RECORDED
        stage = RuleStage.ACCEPTANCE
        requires = frozenset({RuleId.QA_IN_SCOPE_ZERO_DEFECTS})

    class _CycleB(_StubRule):
        rule_id = RuleId.QA_IN_SCOPE_ZERO_DEFECTS
        condition = TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS
        stage = RuleStage.ACCEPTANCE
        requires = frozenset({RuleId.QA_FINAL_PASS_RECORDED})

    with pytest.raises(RuleDefinitionError, match="does not sort strictly earlier"):
        RuleEngine((_CycleA(), _CycleB()))


def test_a_self_referencing_prerequisite_is_rejected() -> None:
    """Verifies a rule cannot be its own prerequisite."""

    class _SelfDependentStub(_StubRule):
        rule_id = RuleId.WORKER_CAPABILITY_MATCHES
        condition = TransitionCondition.WORKER_CAPABILITY_MATCHES
        stage = RuleStage.ACTOR_AUTHORITY
        requires = frozenset({RuleId.WORKER_CAPABILITY_MATCHES})

    with pytest.raises(RuleDefinitionError, match="does not sort strictly earlier"):
        RuleEngine((_SelfDependentStub(),))


def test_a_misattributed_result_is_rejected(empty_context: RuleContext) -> None:
    """Verifies a rule cannot return a result attributed to another rule."""
    engine = RuleEngine((_MisattributedStub(),))
    with pytest.raises(RuleDefinitionError, match="attributed to"):
        engine.evaluate([TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context)


# --------------------------------------------------------------------------
# Fail-closed context
# --------------------------------------------------------------------------


def test_a_missing_required_fact_fails_closed(empty_context: RuleContext) -> None:
    """Verifies a rule never passes because the caller forgot a fact (ADR-004 4.4)."""
    engine = RuleEngine((_FactHungryStub(),))
    with pytest.raises(RuleContextIncompleteError) as excinfo:
        engine.evaluate([TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context)
    assert excinfo.value.rule_id == RuleId.WORKER_CAPABILITY_MATCHES
    assert excinfo.value.missing_facts == ("candidate_worker", "task")


def test_the_incomplete_context_error_names_only_the_absent_facts(
    backend_worker: Actor,
) -> None:
    """Verifies the error identifies exactly what the caller must still supply."""
    engine = RuleEngine((_FactHungryStub(),))
    with pytest.raises(RuleContextIncompleteError) as excinfo:
        engine.evaluate(
            [TransitionCondition.WORKER_CAPABILITY_MATCHES],
            RuleContext(candidate_worker=backend_worker),
        )
    assert excinfo.value.missing_facts == ("task",)


def test_required_facts_are_verified_before_any_rule_runs(feature: Feature, task: Task) -> None:
    """Verifies an incomplete context is reported the same way regardless of failures.

    Checking up front keeps the outcome independent of which rule happens to
    fail first.
    """
    engine = RuleEngine((_FactHungryStub(), _DependencyStub(outcome=False)))
    with pytest.raises(RuleContextIncompleteError) as excinfo:
        engine.evaluate(
            [
                TransitionCondition.WORKER_CAPABILITY_MATCHES,
                TransitionCondition.DEPENDENCIES_ACCEPTED,
            ],
            RuleContext(feature=feature, task=task),
        )
    assert excinfo.value.missing_facts == ("candidate_worker",)


def test_a_fact_supplied_as_empty_is_not_missing(feature: Feature) -> None:
    """Verifies an empty tuple is a real fact, distinct from an unsupplied one."""
    context = RuleContext(feature=feature, feature_tasks=())
    assert context.has(RuleFact.FEATURE_TASKS)
    assert context.missing(frozenset({RuleFact.FEATURE_TASKS})) == ()


# --------------------------------------------------------------------------
# Result contract
# --------------------------------------------------------------------------


def test_a_failure_carries_structured_details(empty_context: RuleContext) -> None:
    """Verifies failures are actionable structured data, not prose (ADR-004 4.5)."""
    evaluation = RuleEngine((_AuthorityStub(outcome=False),)).evaluate(
        [TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context
    )
    failure = evaluation.failures[0]
    assert failure.details == (RuleDetail(key="stub", values=(RuleId.WORKER_CAPABILITY_MATCHES,)),)
    assert failure.detail("stub") == (RuleId.WORKER_CAPABILITY_MATCHES,)
    assert failure.detail("absent") == ()


def test_a_passed_result_cannot_carry_a_code() -> None:
    """Verifies result well-formedness is an enforced invariant."""
    with pytest.raises(ValueError, match="PASSED rule result cannot carry"):
        RuleResult(
            rule_id=RuleId.ALL_TASKS_ACCEPTED,
            condition=TransitionCondition.ALL_TASKS_ACCEPTED,
            status=RuleStatus.PASSED,
            code=RuleCode.TASK_NOT_ACCEPTED,
        )


def test_a_failed_result_must_carry_a_code() -> None:
    """Verifies a failure always carries the machine contract."""
    with pytest.raises(ValueError, match="FAILED rule result must carry"):
        RuleResult(
            rule_id=RuleId.ALL_TASKS_ACCEPTED,
            condition=TransitionCondition.ALL_TASKS_ACCEPTED,
            status=RuleStatus.FAILED,
            message="something went wrong",
        )


def test_a_failed_result_must_explain_itself() -> None:
    """Verifies a failure always carries a human-readable message."""
    with pytest.raises(ValueError, match="must explain the failure"):
        RuleResult(
            rule_id=RuleId.ALL_TASKS_ACCEPTED,
            condition=TransitionCondition.ALL_TASKS_ACCEPTED,
            status=RuleStatus.FAILED,
            code=RuleCode.TASK_NOT_ACCEPTED,
        )


def test_a_skipped_result_must_name_its_cause() -> None:
    """Verifies a skip is always explained by the prerequisite that caused it."""
    with pytest.raises(ValueError, match="must name the prerequisites"):
        RuleResult(
            rule_id=RuleId.ALL_TASKS_ACCEPTED,
            condition=TransitionCondition.ALL_TASKS_ACCEPTED,
            status=RuleStatus.SKIPPED,
        )


def test_a_skipped_result_cannot_carry_a_code() -> None:
    """Verifies a skip is never dressed up as a failure."""
    with pytest.raises(ValueError, match="SKIPPED rule result cannot carry"):
        RuleResult(
            rule_id=RuleId.ALL_TASKS_ACCEPTED,
            condition=TransitionCondition.ALL_TASKS_ACCEPTED,
            status=RuleStatus.SKIPPED,
            code=RuleCode.TASK_NOT_ACCEPTED,
            skipped_because=(RuleId.QA_FINAL_PASS_RECORDED,),
        )


def test_only_a_skipped_result_may_name_a_skip_cause() -> None:
    """Verifies a passing rule cannot claim it was skipped."""
    with pytest.raises(ValueError, match="Only a SKIPPED rule result"):
        RuleResult(
            rule_id=RuleId.ALL_TASKS_ACCEPTED,
            condition=TransitionCondition.ALL_TASKS_ACCEPTED,
            status=RuleStatus.PASSED,
            skipped_because=(RuleId.QA_FINAL_PASS_RECORDED,),
        )


def test_rule_status_has_no_not_applicable_member() -> None:
    """Verifies NOT_APPLICABLE stays deliberately absent (ADR-004 4.5)."""
    assert [status.value for status in RuleStatus] == ["PASSED", "FAILED", "SKIPPED"]


def test_raise_if_rejected_raises_on_a_failure(empty_context: RuleContext) -> None:
    """Verifies a rejection can be surfaced as a structured exception."""
    evaluation = RuleEngine((_AuthorityStub(outcome=False),)).evaluate(
        [TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context
    )
    with pytest.raises(RulesRejectedError) as excinfo:
        evaluation.raise_if_rejected()
    assert excinfo.value.evaluation is evaluation
    assert "TASK_NOT_ACCEPTED" in excinfo.value.message


def test_raise_if_rejected_is_silent_when_satisfied(empty_context: RuleContext) -> None:
    """Verifies a satisfied evaluation raises nothing."""
    evaluation = RuleEngine((_AuthorityStub(),)).evaluate(
        [TransitionCondition.WORKER_CAPABILITY_MATCHES], empty_context
    )
    evaluation.raise_if_rejected()


def test_a_result_detail_rejects_a_mutable_value_sequence() -> None:
    """Verifies structured details are immutable in depth."""
    payload: dict[str, Any] = {"key": "ids", "values": ["a", "b"]}
    with pytest.raises(TypeError, match="immutable tuple"):
        RuleDetail(**payload)
