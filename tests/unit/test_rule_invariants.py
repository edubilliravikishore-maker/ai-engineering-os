"""Architectural invariants of the rule layer (ADR-004 4.3, 4.4, 4.6, 4.11, 4.13).

These tests pin properties that must remain true regardless of which rules
exist: the condition vocabulary is fully classified, the registry's machine
identifiers are stable, the context is immutable in depth, and rules mutate
nothing.
"""

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
    """Pins the ADR-004 4.11 counts so a silent reclassification is visible."""
    assert len(IMPLEMENTED_CONDITIONS) == 6
    assert len(PENDING_RULE_EXPANSION) == 17
    assert len(SATISFIED_BY_DOMAIN_INVARIANT) == 4
    assert len(BLOCKED_CONDITIONS) == 4
    assert len(TransitionCondition) == 31


def test_implemented_conditions_are_derived_from_the_registry() -> None:
    """Verifies the implemented set cannot drift from the rules that exist."""
    assert frozenset(rule.condition for rule in RULES) == IMPLEMENTED_CONDITIONS


def test_originating_plan_active_is_declared_but_not_implemented() -> None:
    """Verifies ADR-004 4.8 lands the declaration while its rule stays deferred."""
    condition = TransitionCondition.ORIGINATING_PLAN_ACTIVE
    assert condition in PENDING_RULE_EXPANSION
    assert condition not in IMPLEMENTED_CONDITIONS
    assert RULE_ENGINE.rule_for(condition) is None


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
        condition_classification(TransitionCondition.ORIGINATING_PLAN_ACTIVE)
        == "PENDING_RULE_EXPANSION"
    )
    assert (
        condition_classification(TransitionCondition.REVIEW_NOTES_PRESENT)
        == "SATISFIED_BY_DOMAIN_INVARIANT"
    )
    assert condition_classification(TransitionCondition.REVIEWER_ASSIGNED) == "BLOCKED_CONDITIONS"


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


def test_the_checkpoint_6_gate_status_is_recorded_and_still_outstanding() -> None:
    """Records the ADR-004 4.12 gate status, which fails at Checkpoint 3 by design.

    Eight of the twenty-four required conditions are covered. This is not an
    assertion that the gate passes: it pins the shortfall so Checkpoint 6 cannot
    go live without the gap being noticed.
    """
    covered = FOUNDATION_V1_REQUIRED_CONDITIONS & (
        IMPLEMENTED_CONDITIONS | SATISFIED_BY_DOMAIN_INVARIANT
    )
    outstanding = FOUNDATION_V1_REQUIRED_CONDITIONS - covered
    assert len(covered) == 8
    assert len(outstanding) == 16
    assert len(outstanding & PENDING_RULE_EXPANSION) == 12
    assert BLOCKED_CONDITIONS <= FOUNDATION_V1_REQUIRED_CONDITIONS


# --------------------------------------------------------------------------
# Stable machine identifiers (ADR-004 4.5)
# --------------------------------------------------------------------------


def test_rule_ids_are_stable() -> None:
    """Pins every rule identifier, so a rename is a reviewed breaking change."""
    assert [member.value for member in RuleId] == [
        "worker_capability_matches",
        "dependencies_accepted",
        "system_evidence_required",
        "all_tasks_accepted",
        "qa_final_pass_recorded",
        "qa_in_scope_zero_defects",
    ]


def test_rule_codes_are_stable() -> None:
    """Pins every failure code, which is the contract software depends on."""
    assert [member.value for member in RuleCode] == [
        "WORKER_CAPABILITY_MISMATCH",
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
        RuleId.WORKER_CAPABILITY_MATCHES,
        RuleId.DEPENDENCIES_ACCEPTED,
        RuleId.SYSTEM_EVIDENCE_REQUIRED,
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


def test_the_context_declares_only_the_seven_approved_facts() -> None:
    """Verifies the fact vocabulary stays minimal (ADR-004 4.4)."""
    fields = {field.name for field in dataclasses.fields(RuleContext)}
    assert fields == {fact.value for fact in RuleFact}
    assert len(fields) == 7


def test_the_context_has_no_known_feature_ids_fact() -> None:
    """Verifies ADR-004 4.16: the seven approved facts are unchanged.

    Detecting a dangling Feature reference would need an eighth fact. Checkpoint
    3 deliberately does not add one, so the limitation stays visible instead of
    being papered over with an invented lookup.
    """
    fields = {field.name for field in dataclasses.fields(RuleContext)}
    assert "known_feature_ids" not in fields
    assert "known_features" not in fields
    assert not any("feature_id" in name for name in fields)
    assert RuleFact.__members__.keys() == {
        "CANDIDATE_WORKER",
        "TASK",
        "FEATURE",
        "FEATURE_TASKS",
        "REFERENCED_TASKS",
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
    return RuleContext(
        candidate_worker=worker,
        task=task,
        feature=feature,
        feature_tasks=(task,),
        referenced_tasks=(),
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
    """Demonstrates the two-step relationship without composing it into a Kernel.

    The state machine answers *"is this transition structurally defined, and may
    this initiator request it?"*. The rule engine then answers *"are the
    conditions this edge declares satisfied by these facts?"*. Loading facts,
    mutating state, recording audit, and publishing events belong to the
    Checkpoint 6 Kernel, which does not exist yet — so this test performs the
    two steps by hand rather than through a composer.
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
    assert evaluation.unevaluated_conditions == (TransitionCondition.WORKER_IS_ACTIVE,)
    assert worker_id == backend_worker.id


def test_a_structurally_rejected_transition_is_not_the_rule_engines_concern() -> None:
    """Verifies the rule engine never re-answers the state machine's question."""
    transition = TASK_STATE_MACHINE.evaluate(
        TaskStatus.READY, TaskStatus.ACCEPTED, ActorRole.COORDINATOR
    )
    assert not transition.is_allowed
    assert transition.required_conditions == frozenset()
    assert RULE_ENGINE.evaluate(transition.required_conditions, RuleContext()).results == ()


def test_no_kernel_composer_or_orchestrator_was_created() -> None:
    """Verifies no component yet loads, validates, and mutates in one place.

    ``events`` exists as of Checkpoint 5 and is checked rather than forbidden:
    it announces what ``storage`` recorded and holds exactly four modules. The
    component that will assemble a `RuleContext`, evaluate, mutate, and publish
    is the Checkpoint 6 Kernel, and ``core`` is still absent (ADR-004 4.4, 4.7).
    """
    import ai_engineering_os

    package_root = Path(str(ai_engineering_os.__file__)).parent
    assert not (package_root / "core").exists()
    assert not (package_root / "api").exists()
    event_modules = sorted(path.name for path in (package_root / "events").glob("*.py"))
    assert event_modules == ["__init__.py", "bus.py", "listener.py", "types.py"]
    rules_modules = sorted(path.name for path in (package_root / "rules").glob("*.py"))
    assert rules_modules == [
        "__init__.py",
        "acceptance.py",
        "authority.py",
        "base.py",
        "codes.py",
        "context.py",
        "dependencies.py",
        "engine.py",
        "evidence.py",
        "registry.py",
        "results.py",
    ]
