"""Architectural invariants of the rule layer (ADR-004 4.3, 4.4, 4.6, 4.11, 4.13).

These tests pin properties that must remain true regardless of which rules
exist: the condition vocabulary is fully classified, the registry's machine
identifiers are stable, the context is immutable in depth, and rules mutate
nothing.
"""

import ast
import dataclasses
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    Feature,
    FeaturePlan,
    FeatureStatus,
    PlanStatus,
    Task,
    TaskId,
    TaskStatus,
    TransitionCondition,
    new_id,
)
from ai_engineering_os.domain.errors import RuleDefinitionError
from ai_engineering_os.rules import (
    BLOCKED_CONDITIONS,
    FOUNDATION_V1_REQUIRED_CONDITIONS,
    IMPLEMENTED_CONDITIONS,
    PENDING_RULE_EXPANSION,
    RULE_ENGINE,
    RULES,
    SATISFIED_BY_DOMAIN_INVARIANT,
    Rule,
    RuleCode,
    RuleContext,
    RuleFact,
    RuleId,
    RuleStage,
    condition_classification,
    evaluation_order,
)
from ai_engineering_os.state import (
    FEATURE_PLAN_STATE_MACHINE,
    FEATURE_STATE_MACHINE,
    TASK_STATE_MACHINE,
    StateMachine,
)

_CLASSIFICATION_SETS: tuple[frozenset[TransitionCondition], ...] = (
    IMPLEMENTED_CONDITIONS,
    PENDING_RULE_EXPANSION,
    SATISFIED_BY_DOMAIN_INVARIANT,
    BLOCKED_CONDITIONS,
)


# --------------------------------------------------------------------------
# Four-way condition classification (ADR-004 4.11)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("condition", list(TransitionCondition), ids=lambda c: c.value)
def test_every_condition_is_classified_exactly_once(condition: TransitionCondition) -> None:
    """Verifies the four sets partition the vocabulary.

    No condition may be silently unenforced, and none may be counted twice to
    make a total work out.
    """
    memberships = [members for members in _CLASSIFICATION_SETS if condition in members]
    assert len(memberships) == 1, f"{condition} is classified {len(memberships)} times"


def test_the_classification_covers_the_whole_vocabulary() -> None:
    """Verifies the union of the four sets is the vocabulary itself."""
    union: frozenset[TransitionCondition] = frozenset().union(*_CLASSIFICATION_SETS)
    assert union == frozenset(TransitionCondition)


def test_the_documented_classification_counts_hold() -> None:
    """Pins the ADR-004 4.11 counts so a silent reclassification is visible.

    Checkpoint 3 left 6 implemented and 4 blocked. Checkpoint 6 wrote fifteen
    rules — the twelve the vertical slice walks that were deferred by scope, and
    the three ADR-007 unblocked — leaving one blocked entry that needs no rule.
    """
    assert len(IMPLEMENTED_CONDITIONS) == 21
    assert len(PENDING_RULE_EXPANSION) == 5
    assert len(SATISFIED_BY_DOMAIN_INVARIANT) == 4
    assert len(BLOCKED_CONDITIONS) == 1
    assert len(TransitionCondition) == 31


def test_implemented_conditions_are_derived_from_the_registry() -> None:
    """Verifies the implemented set cannot drift from the rules that exist."""
    assert frozenset(rule.condition for rule in RULES) == IMPLEMENTED_CONDITIONS


def test_originating_plan_active_is_now_enforced() -> None:
    """ADR-004 4.8 declared it and ADR-003 3.12 owed its rule to Checkpoint 6.

    The inverse of the assertion Checkpoint 3 carried: the condition was
    declared on both `-> READY` edges with no rule behind it, and existence
    conferring no execution authority depended on that rule eventually being
    written. It is.
    """
    condition = TransitionCondition.ORIGINATING_PLAN_ACTIVE
    assert condition in IMPLEMENTED_CONDITIONS
    assert condition not in PENDING_RULE_EXPANSION
    assert RULE_ENGINE.rule_for(condition) is not None


def test_every_condition_adr_007_unblocked_is_enforced() -> None:
    """The three Builder rulings of ADR-007 each landed as a real rule.

    A ruling recorded in an ADR but never enforced would be worse than the
    blocked condition it replaced: the gate would show covered where nothing
    checks.
    """
    for condition in (
        TransitionCondition.ALL_IMPLEMENTATION_TASKS_ACCEPTED,
        TransitionCondition.MANDATORY_EVIDENCE_PRESENT,
        TransitionCondition.REVIEWER_ASSIGNED,
    ):
        assert condition in IMPLEMENTED_CONDITIONS, condition
        assert condition not in BLOCKED_CONDITIONS, condition
        assert RULE_ENGINE.rule_for(condition) is not None, condition


def test_tasks_instantiated_stays_blocked_and_is_discharged_by_the_runner() -> None:
    """ADR-007 7.5: the one blocked entry that never needed a Builder ruling.

    Plan activation *performs* the instantiation, so a rule evaluated before the
    runner acts would be meaningless. The Transition Runner asserts the outcome
    it has just produced, inside the same transaction.
    """
    condition = TransitionCondition.TASKS_INSTANTIATED
    assert frozenset({condition}) == BLOCKED_CONDITIONS
    assert RULE_ENGINE.rule_for(condition) is None
    assert condition in FOUNDATION_V1_REQUIRED_CONDITIONS


@pytest.mark.parametrize(
    "condition",
    sorted(BLOCKED_CONDITIONS),
    ids=lambda c: c.value,
)
def test_a_blocked_condition_has_no_rule(condition: TransitionCondition) -> None:
    """Verifies an owed Builder decision was never quietly implemented."""
    assert RULE_ENGINE.rule_for(condition) is None


def test_classification_lookup_names_the_owning_set() -> None:
    """Verifies each condition reports which classification governs it."""
    assert (
        condition_classification(TransitionCondition.WORKER_CAPABILITY_MATCHES)
        == "IMPLEMENTED_CONDITIONS"
    )
    assert (
        condition_classification(TransitionCondition.QA_REPORT_FAILED) == "PENDING_RULE_EXPANSION"
    )
    assert (
        condition_classification(TransitionCondition.REVIEW_NOTES_PRESENT)
        == "SATISFIED_BY_DOMAIN_INVARIANT"
    )
    assert condition_classification(TransitionCondition.TASKS_INSTANTIATED) == "BLOCKED_CONDITIONS"


# --------------------------------------------------------------------------
# Registry and state-machine agreement
# --------------------------------------------------------------------------


def _declared_conditions(*machines: StateMachine[Any]) -> frozenset[TransitionCondition]:
    return frozenset(
        condition
        for machine in machines
        for transition in machine.transitions
        for condition in transition.required_conditions
    )


def test_every_registered_rule_evaluates_a_declared_condition() -> None:
    """Verifies no rule invents a requirement the architecture never declared."""
    declared = _declared_conditions(FEATURE_STATE_MACHINE, TASK_STATE_MACHINE)
    for rule in RULES:
        assert rule.condition in declared, f"{rule.rule_id} evaluates an undeclared condition"


def test_the_work_package_lifecycle_declares_no_condition() -> None:
    """Verifies ADR-003 3.5: no Work Package rule may exist to compete for authority."""
    from ai_engineering_os.state import WORK_PACKAGE_STATE_MACHINE

    assert _declared_conditions(WORK_PACKAGE_STATE_MACHINE) == frozenset()


def _derive_required_conditions(
    *,
    feature_sm: StateMachine[Any],
    plan_sm: StateMachine[Any],
    task_sm: StateMachine[Any],
) -> frozenset[TransitionCondition]:
    """Derives the required-condition set from the Blueprint 10.2 slice edges.

    Conditions are always read from the **live** ``TransitionDefinition`` objects
    of the supplied machines. Nothing about the conditions is hard-coded here;
    only the edge list is, because Blueprint 10.2 is prose rather than a
    machine-readable structure.
    """
    slice_edges: tuple[tuple[StateMachine[Any], Any, Any], ...] = (
        # Step 4 — Feature planning and plan activation
        (feature_sm, FeatureStatus.DRAFT, FeatureStatus.PLANNED),
        (feature_sm, FeatureStatus.PLANNED, FeatureStatus.IN_PROGRESS),
        (plan_sm, PlanStatus.DRAFT, PlanStatus.READY),
        (plan_sm, PlanStatus.READY, PlanStatus.ACTIVE),
        (task_sm, TaskStatus.CREATED, TaskStatus.READY),
        # Step 5 — assignment and start
        (task_sm, TaskStatus.READY, TaskStatus.ASSIGNED),
        (task_sm, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS),
        # Steps 6 and 7 — rejected and accepted submission
        (task_sm, TaskStatus.IN_PROGRESS, TaskStatus.SUBMITTED),
        # Step 8 — independent review
        (task_sm, TaskStatus.SUBMITTED, TaskStatus.IN_REVIEW),
        (task_sm, TaskStatus.IN_REVIEW, TaskStatus.IN_QA),
        # Step 9 — QA validation
        (task_sm, TaskStatus.IN_QA, TaskStatus.ACCEPTED),
        # Step 10 — Feature acceptance
        (feature_sm, FeatureStatus.IN_PROGRESS, FeatureStatus.IN_VALIDATION),
        (feature_sm, FeatureStatus.IN_VALIDATION, FeatureStatus.ACCEPTED),
    )
    derived: set[TransitionCondition] = set()
    for machine, from_state, to_state in slice_edges:
        definition = machine.definition(from_state, to_state)
        assert definition is not None, f"{from_state} -> {to_state} is not defined"
        derived |= definition.required_conditions
    return frozenset(derived)


def _plan_machine_with(
    from_state: PlanStatus, to_state: PlanStatus, condition: TransitionCondition
) -> StateMachine[PlanStatus]:
    """Builds a throwaway Feature Plan machine carrying one extra condition.

    Constructed from the public ``transitions`` property, so nothing on disk and
    no shared module-level machine is mutated.
    """
    transitions = tuple(
        dataclasses.replace(
            transition, required_conditions=transition.required_conditions | {condition}
        )
        if transition.key == (from_state, to_state)
        else transition
        for transition in FEATURE_PLAN_STATE_MACHINE.transitions
    )
    return StateMachine(
        entity="FeaturePlanProbe",
        state_type=PlanStatus,
        initial_state=PlanStatus.DRAFT,
        transitions=transitions,
    )


def test_the_foundation_v1_required_set_is_derived_from_the_vertical_slice() -> None:
    """Verifies ADR-004 4.13: the gate set is derived, never authored separately.

    The rules layer states the result because it must not import ``state``; this
    test re-derives it from the live state machines so the two cannot drift.
    """
    derived = _derive_required_conditions(
        feature_sm=FEATURE_STATE_MACHINE,
        plan_sm=FEATURE_PLAN_STATE_MACHINE,
        task_sm=TASK_STATE_MACHINE,
    )
    assert derived == FOUNDATION_V1_REQUIRED_CONDITIONS
    assert len(FOUNDATION_V1_REQUIRED_CONDITIONS) == 24


def test_the_feature_plan_slice_edges_declare_no_condition_today() -> None:
    """Verifies the two Plan edges contribute nothing, keeping the union at 24."""
    for from_state, to_state in (
        (PlanStatus.DRAFT, PlanStatus.READY),
        (PlanStatus.READY, PlanStatus.ACTIVE),
    ):
        definition = FEATURE_PLAN_STATE_MACHINE.definition(from_state, to_state)
        assert definition is not None
        assert definition.required_conditions == frozenset()


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (PlanStatus.DRAFT, PlanStatus.READY),
        (PlanStatus.READY, PlanStatus.ACTIVE),
    ],
    ids=["DRAFT->READY", "READY->ACTIVE"],
)
def test_a_condition_added_to_a_plan_slice_edge_breaks_the_derivation(
    from_state: PlanStatus, to_state: PlanStatus
) -> None:
    """Verifies the derivation actually walks both Feature Plan edges.

    Without this, a condition added to a Plan edge the slice walks would go
    undetected and the Checkpoint 6 gate set would silently under-report.
    """
    probe_condition = TransitionCondition.TASK_HAS_DEPENDENCIES
    assert probe_condition not in FOUNDATION_V1_REQUIRED_CONDITIONS

    derived = _derive_required_conditions(
        feature_sm=FEATURE_STATE_MACHINE,
        plan_sm=_plan_machine_with(from_state, to_state, probe_condition),
        task_sm=TASK_STATE_MACHINE,
    )
    assert probe_condition in derived
    assert derived != FOUNDATION_V1_REQUIRED_CONDITIONS
    assert len(derived) == 25

    # The shared machine is untouched: the baseline derivation still holds.
    assert (
        _derive_required_conditions(
            feature_sm=FEATURE_STATE_MACHINE,
            plan_sm=FEATURE_PLAN_STATE_MACHINE,
            task_sm=TASK_STATE_MACHINE,
        )
        == FOUNDATION_V1_REQUIRED_CONDITIONS
    )


def test_the_checkpoint_6_gate_passes() -> None:
    """The ADR-004 4.12 gate, which failed at Checkpoint 3 by design.

    This is the assertion Checkpoint 3 could not make. Twenty-three of the
    twenty-four required conditions are enforced by a rule or guaranteed by a
    proven domain invariant.

    The twenty-fourth is ``TASKS_INSTANTIATED``, and it is not a shortfall: the
    Transition Runner performs the instantiation inside the transaction and
    asserts the outcome it produced (ADR-007 7.5). It is named here explicitly
    rather than counted as covered, because a gate that quietly rounded it up
    would be a gate that could round anything up.
    """
    covered = FOUNDATION_V1_REQUIRED_CONDITIONS & (
        IMPLEMENTED_CONDITIONS | SATISFIED_BY_DOMAIN_INVARIANT
    )
    outstanding = FOUNDATION_V1_REQUIRED_CONDITIONS - covered

    assert len(covered) == 23
    assert outstanding == frozenset({TransitionCondition.TASKS_INSTANTIATED})
    assert not outstanding & PENDING_RULE_EXPANSION
    assert BLOCKED_CONDITIONS <= FOUNDATION_V1_REQUIRED_CONDITIONS


# --------------------------------------------------------------------------
# Stable machine identifiers (ADR-004 4.5)
# --------------------------------------------------------------------------


def test_rule_ids_are_stable() -> None:
    """Pins every rule identifier, so a rename is a reviewed breaking change."""
    assert [member.value for member in RuleId] == [
        "worker_capability_matches",
        "worker_is_active",
        "requester_is_assigned_worker",
        "reviewer_assigned",
        "feature_plan_attached",
        "plan_has_task_definitions",
        "plan_is_ready",
        "originating_plan_active",
        "dependencies_accepted",
        "work_package_present",
        "claims_defined",
        "verification_guide_present",
        "system_evidence_required",
        "feature_evidence_present",
        "review_decision_approved",
        "qa_report_passed",
        "test_execution_evidence_present",
        "implementation_tasks_accepted",
        "all_tasks_accepted",
        "qa_final_pass_recorded",
        "qa_in_scope_zero_defects",
    ]


def test_rule_codes_are_stable() -> None:
    """Pins every failure code, which is the contract software depends on."""
    assert [member.value for member in RuleCode] == [
        "WORKER_CAPABILITY_MISMATCH",
        "WORKER_INACTIVE",
        "ACTOR_IS_NOT_A_WORKER",
        "REQUESTER_IS_NOT_THE_ASSIGNED_WORKER",
        "TASK_HAS_NO_ASSIGNED_WORKER",
        "NO_REVIEWER_ROUTED",
        "REVIEWER_NOT_ELIGIBLE",
        "REVIEWER_CAPABILITY_MISMATCH",
        "REVIEWER_PERFORMED_THE_WORK",
        "NO_FEATURE_PLAN_ATTACHED",
        "PLAN_DEFINES_NO_TASKS",
        "PLAN_NOT_READY",
        "ORIGINATING_PLAN_NOT_SUPPLIED",
        "ORIGINATING_PLAN_NOT_ACTIVE",
        "NO_ACTIVE_REVISION",
        "NO_WORK_PACKAGE_SUBMITTED",
        "NO_CLAIMS_DECLARED",
        "NO_VERIFICATION_GUIDE",
        "MISSING_FEATURE_EVIDENCE",
        "NO_REVIEW_DECISION_RECORDED",
        "REVIEW_CHANGES_REQUESTED",
        "NO_QA_REPORT_FOR_REVISION",
        "QA_REPORT_DID_NOT_PASS",
        "NO_TEST_RESULTS_RECORDED",
        "NO_TEST_EXECUTION_EVIDENCE",
        "IMPLEMENTATION_TASK_NOT_ACCEPTED",
        "NO_IMPLEMENTATION_TASKS_RECORDED",
        "DEPENDENCY_NOT_ACCEPTED",
        "DEPENDENCY_FACTS_MISSING",
        "MISSING_SYSTEM_EVIDENCE",
        "EVIDENCE_STANDARD_UNDEFINED",
        "TASK_NOT_ACCEPTED",
        "NO_TASKS_RECORDED",
        "MISSING_QA_FINAL_PASS",
        "INVALID_QA_FINAL_PASS",
        "UNRESOLVED_IN_SCOPE_DEFECT",
        "DEFECT_SCOPE_UNRESOLVED",
    ]


def test_rule_ids_are_not_derived_from_class_names() -> None:
    """Verifies identifiers are declared, so renaming a class cannot rename a contract."""
    for rule in RULES:
        assert rule.rule_id.value != type(rule).__name__


def test_rule_stages_are_numbered_as_approved() -> None:
    """Pins the ADR-004 4.3 stage numbering, including the reserved empty stage."""
    assert [(stage.name, stage.value) for stage in RuleStage] == [
        ("ACTOR_AUTHORITY", 1),
        ("STATE_TRANSITION", 2),
        ("PLAN_DEPENDENCY", 3),
        ("EVIDENCE", 4),
        ("ACCEPTANCE", 5),
    ]


def test_no_registered_rule_occupies_the_state_transition_stage() -> None:
    """Verifies structural transition validity stays with the state machine."""
    assert all(rule.stage is not RuleStage.STATE_TRANSITION for rule in RULES)


def test_the_registry_evaluation_order_is_pinned() -> None:
    """Pins the OS-owned evaluation order of the real registry."""
    assert [rule.rule_id for rule in RULE_ENGINE.rules] == [
        # Stage 1 — Actor / authority
        RuleId.WORKER_IS_ACTIVE,
        RuleId.WORKER_CAPABILITY_MATCHES,
        RuleId.REQUESTER_IS_ASSIGNED_WORKER,
        RuleId.REVIEWER_ASSIGNED,
        # Stage 3 — Plan / dependencies
        RuleId.FEATURE_PLAN_ATTACHED,
        RuleId.PLAN_HAS_TASK_DEFINITIONS,
        RuleId.PLAN_IS_READY,
        RuleId.ORIGINATING_PLAN_ACTIVE,
        RuleId.DEPENDENCIES_ACCEPTED,
        # Stage 4 — Evidence
        RuleId.WORK_PACKAGE_PRESENT,
        RuleId.CLAIMS_DEFINED,
        RuleId.VERIFICATION_GUIDE_PRESENT,
        RuleId.SYSTEM_EVIDENCE_REQUIRED,
        RuleId.FEATURE_EVIDENCE_PRESENT,
        # Stage 5 — Acceptance
        RuleId.REVIEW_DECISION_APPROVED,
        RuleId.QA_REPORT_PASSED,
        RuleId.TEST_EXECUTION_EVIDENCE_PRESENT,
        RuleId.IMPLEMENTATION_TASKS_ACCEPTED,
        RuleId.ALL_TASKS_ACCEPTED,
        RuleId.QA_FINAL_PASS_RECORDED,
        RuleId.QA_IN_SCOPE_ZERO_DEFECTS,
    ]
    assert evaluation_order(RULES) == RULE_ENGINE.rules


def test_the_registry_is_an_immutable_module_level_structure() -> None:
    """Verifies the rule set cannot be extended at runtime."""
    assert isinstance(RULES, tuple)
    assert isinstance(RULE_ENGINE.rules, tuple)
    for mutator in ("append", "extend", "insert", "remove"):
        assert not hasattr(RULE_ENGINE.rules, mutator)


# --------------------------------------------------------------------------
# Context immutability (ADR-004 4.4)
# --------------------------------------------------------------------------


def test_the_context_is_frozen(feature: Feature) -> None:
    """Verifies a rule cannot rebind a context field."""
    context = RuleContext(feature=feature)
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.feature = None  # type: ignore[misc]


def test_the_context_is_immutable_in_depth(feature: Feature, task: Task) -> None:
    """Verifies nested domain facts are frozen, not merely the context surface."""
    context = RuleContext(feature=feature, feature_tasks=(task,))
    feature_fact = context.feature
    task_facts = context.feature_tasks
    assert feature_fact is not None
    assert task_facts is not None
    with pytest.raises(ValidationError):
        feature_fact.status = FeatureStatus.ACCEPTED  # type: ignore[misc]
    with pytest.raises(ValidationError):
        task_facts[0].status = TaskStatus.ACCEPTED  # type: ignore[misc]


def test_the_context_rejects_a_mutable_collection(task: Task) -> None:
    """Verifies immutability is structural, not a caller convention."""
    payload: dict[str, Any] = {"feature_tasks": [task]}
    with pytest.raises(TypeError, match="immutable tuple"):
        RuleContext(**payload)


def test_the_context_declares_exactly_the_approved_facts() -> None:
    """Verifies the fact vocabulary stays minimal (ADR-004 4.4).

    Checkpoint 3 approved seven. Checkpoint 6 added six, each because a rule
    written here consumes it — the requester and candidate Reviewer of the
    authority rules, the Revisions review and QA resolve through, the Plans the
    planning rules read, and the Work Packages and Review Decisions of the
    submission and review gates.

    The count is pinned rather than derived so an eighteenth fact is a reviewed
    decision. ``test_every_context_fact_is_consumed_by_a_registered_rule``
    proves each one earns its place.
    """
    fields = {field.name for field in dataclasses.fields(RuleContext)}
    assert fields == {fact.value for fact in RuleFact}
    assert len(fields) == 13


def test_the_context_has_no_known_feature_ids_fact() -> None:
    """Verifies ADR-004 4.16 survived the Checkpoint 6 fact expansion.

    Detecting a dangling Feature reference would need a lookup fact. Six facts
    were added here, and **none of them is that one**: the recorded limitation
    in ``QAInScopeZeroDefectsRule`` — that an existing different Feature cannot
    be told from a nonexistent Feature identifier — stays visible rather than
    being papered over with an invented lookup while the surface was open.
    """
    fields = {field.name for field in dataclasses.fields(RuleContext)}
    assert "known_feature_ids" not in fields
    assert "known_features" not in fields
    assert not any("feature_id" in name for name in fields)
    assert RuleFact.__members__.keys() == {
        "CANDIDATE_WORKER",
        "CANDIDATE_REVIEWERS",
        "REQUESTING_ACTOR",
        "TASK",
        "TASK_REVISIONS",
        "FEATURE",
        "FEATURE_TASKS",
        "FEATURE_PLANS",
        "REFERENCED_TASKS",
        "WORK_PACKAGES",
        "REVIEW_DECISIONS",
        "EVIDENCE",
        "QA_REPORTS",
    }


def test_the_context_carries_no_infrastructure_fact() -> None:
    """Verifies no session, repository, clock, or config leaked into the fact set."""
    forbidden = {
        "clock",
        "config",
        "connection",
        "database",
        "known_feature_ids",
        "latest_qa_report",
        "loader",
        "now",
        "random",
        "repository",
        "session",
    }
    fields = {field.name for field in dataclasses.fields(RuleContext)}
    assert not fields & forbidden


def test_every_context_fact_is_consumed_by_a_registered_rule() -> None:
    """Verifies a fact exists only because a rule reads it."""
    consumed: set[RuleFact] = set()
    for rule in RULES:
        consumed |= rule.required_facts
    assert consumed == set(RuleFact)


# --------------------------------------------------------------------------
# Rule purity (ADR-004 4.6)
# --------------------------------------------------------------------------


def _full_context(feature: Feature, task: Task, worker: Actor) -> RuleContext:
    """A context supplying every fact, so every registered rule can be evaluated."""
    return RuleContext(
        candidate_worker=worker,
        candidate_reviewers=(worker,),
        requesting_actor=worker,
        task=task,
        task_revisions=(),
        feature=feature,
        feature_tasks=(task,),
        feature_plans=(),
        referenced_tasks=(),
        work_packages=(),
        review_decisions=(),
        evidence=(),
        qa_reports=(),
    )


def test_evaluation_does_not_mutate_the_context(
    feature: Feature, task: Task, backend_worker: Actor
) -> None:
    """Verifies a rule evaluates and returns, changing nothing."""
    context = _full_context(feature, task, backend_worker)
    before = (
        feature.model_dump(),
        task.model_dump(),
        backend_worker.model_dump(),
        dataclasses.asdict(context),
    )
    RULE_ENGINE.evaluate(list(TransitionCondition), context)
    assert (
        feature.model_dump(),
        task.model_dump(),
        backend_worker.model_dump(),
        dataclasses.asdict(context),
    ) == before


def test_evaluation_is_repeatable_against_the_real_registry(
    feature: Feature, task: Task, backend_worker: Actor
) -> None:
    """Verifies the OS engine is reproducible against real rules and real facts."""
    context = _full_context(feature, task, backend_worker)
    conditions = list(TransitionCondition)
    first = RULE_ENGINE.evaluate(conditions, context)
    assert RULE_ENGINE.evaluate(conditions, context) == first
    assert len(first.unevaluated_conditions) == len(TransitionCondition) - len(RULES)


def test_rules_are_stateless(feature: Feature, task: Task, backend_worker: Actor) -> None:
    """Verifies a rule instance accumulates no evaluation state."""
    context = _full_context(feature, task, backend_worker)
    rule = RULES[0]
    assert not getattr(rule, "__dict__", {})
    first = rule.evaluate(context)
    assert rule.evaluate(context) == first


def test_the_rule_contract_is_abstract() -> None:
    """Verifies rules implement one explicit contract rather than a duck type."""
    with pytest.raises(TypeError):
        Rule()  # type: ignore[abstract]


def test_no_rule_declares_an_undefined_prerequisite() -> None:
    """Verifies prerequisite edges only reference registered rules."""
    registered = {rule.rule_id for rule in RULES}
    for rule in RULES:
        assert rule.requires <= registered


def test_a_condition_classified_as_a_domain_invariant_has_no_rule() -> None:
    """Verifies no unfalsifiable rule was written for a guaranteed condition."""
    for condition in SATISFIED_BY_DOMAIN_INVARIANT:
        assert RULE_ENGINE.rule_for(condition) is None


def test_an_unclassified_condition_is_rejected() -> None:
    """Verifies the classification lookup fails closed rather than guessing."""

    unknown: Any = "NOT_A_CONDITION"
    with pytest.raises(RuleDefinitionError, match="not classified"):
        condition_classification(unknown)


# --------------------------------------------------------------------------
# Architecture boundary (ADR-004 4.7)
# --------------------------------------------------------------------------


def test_the_state_machine_and_the_rule_engine_answer_different_questions(
    feature: Feature, feature_plan: FeaturePlan, backend_worker: Actor, worker_id: ActorId
) -> None:
    """Demonstrates the two-step relationship, performed here by hand.

    The state machine answers *"is this transition structurally defined, and may
    this initiator request it?"*. The rule engine then answers *"are the
    conditions this edge declares satisfied by these facts?"*.

    The Kernel composes those two steps and adds mutation, audit and event
    publication around them. This test deliberately does **not** go through the
    Kernel: it pins that the two components remain separable and that neither
    re-answers the other's question, which is what makes the Kernel's ordering
    verifiable rather than tangled.

    Both conditions on this edge are now evaluated. At Checkpoint 3
    ``WORKER_IS_ACTIVE`` came back unevaluated, and the assertion below is the
    inverse of the one that recorded it.
    """
    ready_task = Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        feature_plan_id=feature_plan.id,
        plan_definition_key="auth-api",
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
        status=TaskStatus.READY,
    )

    transition = TASK_STATE_MACHINE.evaluate(
        TaskStatus.READY, TaskStatus.ASSIGNED, ActorRole.COORDINATOR
    )
    assert transition.is_allowed

    evaluation = RULE_ENGINE.evaluate(
        transition.required_conditions,
        RuleContext(candidate_worker=backend_worker, task=ready_task),
    )
    assert evaluation.is_satisfied
    assert evaluation.unevaluated_conditions == ()
    assert worker_id == backend_worker.id


def test_a_structurally_rejected_transition_is_not_the_rule_engines_concern() -> None:
    """Verifies the rule engine never re-answers the state machine's question."""
    transition = TASK_STATE_MACHINE.evaluate(
        TaskStatus.READY, TaskStatus.ACCEPTED, ActorRole.COORDINATOR
    )
    assert not transition.is_allowed
    assert transition.required_conditions == frozenset()
    assert RULE_ENGINE.evaluate(transition.required_conditions, RuleContext()).results == ()


def test_the_kernel_is_the_only_composer() -> None:
    """Verifies exactly one component loads, validates, mutates and publishes.

    The inverse of the assertion Checkpoint 3 through 5 carried, which pinned
    that ``core`` did not exist yet. It does now, and the property that matters
    is no longer its absence but its **uniqueness**: composition in two places
    is how the Validation-First ordering of Blueprint 7.2 gets lost.

    ``api`` is still absent — that is Checkpoint 7.
    """
    import ai_engineering_os

    package_root = Path(str(ai_engineering_os.__file__)).parent
    assert (package_root / "core").exists()
    assert not (package_root / "api").exists()

    core_modules = sorted(path.name for path in (package_root / "core").glob("*.py"))
    assert core_modules == [
        "__init__.py",
        "context_loader.py",
        "kernel.py",
        "routing.py",
        "runner.py",
    ]


@pytest.mark.parametrize(
    "layer",
    ["domain", "state", "rules", "storage", "events"],
)
def test_no_layer_beneath_the_kernel_imports_it(layer: str) -> None:
    """Verifies the dependency direction of Blueprint 2.2 still points one way.

    ``core`` sits above all five and imports four of them. An import back the
    other way would make the Kernel reachable from a component that must not
    mutate, and the boundary that keeps rules pure would exist only by
    convention.
    """
    import ai_engineering_os

    package_root = Path(str(ai_engineering_os.__file__)).parent
    for path in (package_root / layer).rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for name in names:
                assert not name.startswith("ai_engineering_os.core"), f"{path.name}: {name}"


def test_only_the_kernel_calls_the_notification_emitter() -> None:
    """Verifies ADR-006 6.9: the Kernel owns the emit, and owns it in one place.

    Staging an event and emitting its wake-up are two separate calls and are
    **not enforced by construction**. This is the required Checkpoint 6 check:
    the emit is called from exactly one module, next to the append it announces,
    so a caller cannot do the first and omit the second.
    """
    import ai_engineering_os

    package_root = Path(str(ai_engineering_os.__file__)).parent
    callers = {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*.py")
        if "emit_for_event(" in path.read_text(encoding="utf-8")
        and path.name not in {"bus.py", "__init__.py"}
    }
    assert callers == {"core/runner.py"}
