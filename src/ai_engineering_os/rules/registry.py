"""The immutable rule registry and condition classification (ADR-004 4.3, 4.11).

Three things live here:

1. ``RULES`` — the registered rule set, in declaration order. Order inside a
   stage is this tuple's order. The registry is a module-level constant: there
   is no runtime registration path, because enforcement that can be changed at
   runtime is enforcement that is not reproducible.
2. The **four-way condition classification**, which partitions the entire
   condition vocabulary so no requirement can be silently unenforced.
3. ``FOUNDATION_V1_REQUIRED_CONDITIONS`` — the Checkpoint 6 safety gate set.

The partition and the required-condition derivation are both verified at import
time and pinned by test.
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.errors import RuleDefinitionError
from ai_engineering_os.rules.acceptance import (
    AllTasksAcceptedRule,
    ImplementationTasksAcceptedRule,
    QAFinalPassRecordedRule,
    QAInScopeZeroDefectsRule,
)
from ai_engineering_os.rules.authority import (
    RequesterIsAssignedWorkerRule,
    ReviewerAssignedRule,
    WorkerCapabilityMatchesRule,
    WorkerIsActiveRule,
)
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.dependencies import DependenciesAcceptedRule
from ai_engineering_os.rules.engine import RuleEngine
from ai_engineering_os.rules.evidence import FeatureEvidenceRequiredRule, SystemEvidenceRequiredRule
from ai_engineering_os.rules.planning import (
    FeaturePlanAttachedRule,
    OriginatingPlanActiveRule,
    PlanHasTaskDefinitionsRule,
    PlanIsReadyRule,
)
from ai_engineering_os.rules.submission import (
    ClaimsDefinedRule,
    VerificationGuidePresentRule,
    WorkPackagePresentRule,
)
from ai_engineering_os.rules.verification import (
    QAReportPassedRule,
    ReviewDecisionApprovedRule,
    TestExecutionEvidencePresentRule,
)

__all__ = [
    "BLOCKED_CONDITIONS",
    "FOUNDATION_V1_REQUIRED_CONDITIONS",
    "IMPLEMENTED_CONDITIONS",
    "PENDING_RULE_EXPANSION",
    "RULES",
    "RULE_ENGINE",
    "SATISFIED_BY_DOMAIN_INVARIANT",
    "condition_classification",
]

RULES: tuple[Rule, ...] = (
    # Stage 1 — Actor / authority
    WorkerIsActiveRule(),
    WorkerCapabilityMatchesRule(),
    RequesterIsAssignedWorkerRule(),
    ReviewerAssignedRule(),
    # Stage 3 — Plan / dependencies
    FeaturePlanAttachedRule(),
    PlanHasTaskDefinitionsRule(),
    PlanIsReadyRule(),
    OriginatingPlanActiveRule(),
    DependenciesAcceptedRule(),
    # Stage 4 — Evidence
    WorkPackagePresentRule(),
    ClaimsDefinedRule(),
    VerificationGuidePresentRule(),
    SystemEvidenceRequiredRule(),
    FeatureEvidenceRequiredRule(),
    # Stage 5 — Acceptance
    ReviewDecisionApprovedRule(),
    QAReportPassedRule(),
    TestExecutionEvidencePresentRule(),
    ImplementationTasksAcceptedRule(),
    AllTasksAcceptedRule(),
    QAFinalPassRecordedRule(),
    QAInScopeZeroDefectsRule(),
)
"""Every rule the OS enforces today, in declaration order.

Stage 2 (state transition) is intentionally empty: structural transition
validity belongs to the state machine, not to a rule (ADR-004 4.3).
"""

RULE_ENGINE: RuleEngine = RuleEngine(RULES)
"""The OS rule engine. Constructing it validates the registry."""

IMPLEMENTED_CONDITIONS: frozenset[TransitionCondition] = frozenset(rule.condition for rule in RULES)
"""Conditions a registered rule evaluates today.

Derived from ``RULES`` rather than restated, so this set cannot drift from the
rules that actually exist.
"""

PENDING_RULE_EXPANSION: frozenset[TransitionCondition] = frozenset(
    {
        # Deterministically computable against the current domain model, and
        # deferred by scope decision alone (ADR-004 4.10). Each is a scope
        # decision, never an unanswered architectural question.
        #
        # Every remaining entry governs a **rework or branch edge** that the
        # Foundation v1 vertical slice does not walk (ADR-004 4.13), so none is
        # required by the Checkpoint 6 gate. Checkpoint 6 wrote the twelve that
        # the slice does walk; these are what is left.
        TransitionCondition.TASK_HAS_DEPENDENCIES,
        TransitionCondition.REVIEW_DECISION_CHANGES_REQUESTED,
        TransitionCondition.QA_REPORT_FAILED,
        TransitionCondition.INCREMENTED_REVISION_CREATED,
        TransitionCondition.QA_DEFECT_FINDINGS_RECORDED,
    }
)
"""Computable now, **not yet written** — a scope decision (ADR-004 4.11)."""

SATISFIED_BY_DOMAIN_INVARIANT: frozenset[TransitionCondition] = frozenset(
    {
        # FeaturePlan validates task-key uniqueness, dependency resolvability,
        # and acyclicity at construction.
        TransitionCondition.PLAN_DEPENDENCIES_VALID,
        # ReviewDecision.notes is mandatory non-empty text.
        TransitionCondition.REVIEW_NOTES_PRESENT,
        # Same field, same guarantee.
        TransitionCondition.REVIEW_FEEDBACK_PRESENT,
        # QAReport requires a FAILED report to carry at least one defect, and
        # QADefect requires non-empty title, severity, and priority.
        TransitionCondition.DEFECTS_DOCUMENTED,
    }
)
"""Structurally guaranteed by domain-model construction (ADR-004 4.11).

A rule for these could never fail, so enforcement is discharged by pinning the
guaranteeing validator rather than by writing an unfalsifiable rule.
"""

BLOCKED_CONDITIONS: frozenset[TransitionCondition] = frozenset(
    {
        # Plan activation *performs* the instantiation (ADR-003 3.12), so
        # evaluating it before the runner acts is meaningless. Not an owed
        # decision and never was (ADR-007 7.5): the Transition Runner asserts
        # the outcome it has just produced, inside the same transaction.
        TransitionCondition.TASKS_INSTANTIATED,
    }
)
"""Cannot be written without a Builder ruling or later-checkpoint machinery.

An **owed decision**, deliberately kept distinct from ``PENDING_RULE_EXPANSION``:
collapsing the two would let an unanswered architectural question hide inside a
backlog (ADR-004 4.11).

**Three of the original four were discharged by ADR-007** — the definition of
"implementation task" (7.1), the Feature-level mandatory evidence set (7.2), and
the Reviewer assignment and routing model (7.3). Each is now enforced by a
registered rule above. The fourth entry needed no ruling at all, only the runner.
"""

FOUNDATION_V1_REQUIRED_CONDITIONS: frozenset[TransitionCondition] = frozenset(
    {
        # Feature DRAFT -> PLANNED
        TransitionCondition.FEATURE_PLAN_ATTACHED,
        TransitionCondition.PLAN_HAS_TASK_DEFINITIONS,
        # Feature PLANNED -> IN_PROGRESS
        TransitionCondition.PLAN_IS_READY,
        TransitionCondition.TASKS_INSTANTIATED,
        TransitionCondition.PLAN_DEPENDENCIES_VALID,
        # Task CREATED -> READY
        TransitionCondition.DEPENDENCIES_ACCEPTED,
        TransitionCondition.ORIGINATING_PLAN_ACTIVE,
        # Task READY -> ASSIGNED
        TransitionCondition.WORKER_IS_ACTIVE,
        TransitionCondition.WORKER_CAPABILITY_MATCHES,
        # Task ASSIGNED -> IN_PROGRESS
        TransitionCondition.REQUESTER_IS_ASSIGNED_WORKER,
        # Task IN_PROGRESS -> SUBMITTED
        TransitionCondition.WORK_PACKAGE_PRESENT,
        TransitionCondition.CLAIMS_DEFINED,
        TransitionCondition.MANDATORY_SYSTEM_EVIDENCE_ATTACHED,
        TransitionCondition.VERIFICATION_GUIDE_PRESENT,
        # Task SUBMITTED -> IN_REVIEW
        TransitionCondition.REVIEWER_ASSIGNED,
        # Task IN_REVIEW -> IN_QA
        TransitionCondition.REVIEW_DECISION_APPROVED,
        TransitionCondition.REVIEW_NOTES_PRESENT,
        # Task IN_QA -> ACCEPTED
        TransitionCondition.QA_REPORT_PASSED,
        TransitionCondition.TEST_EXECUTION_EVIDENCE_PRESENT,
        # Feature IN_PROGRESS -> IN_VALIDATION
        TransitionCondition.ALL_IMPLEMENTATION_TASKS_ACCEPTED,
        # Feature IN_VALIDATION -> ACCEPTED
        TransitionCondition.ALL_TASKS_ACCEPTED,
        TransitionCondition.QA_FINAL_PASS_RECORDED,
        TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS,
        TransitionCondition.MANDATORY_EVIDENCE_PRESENT,
    }
)
"""The conditions the approved Foundation v1 vertical slice actually walks.

Derived from the transitions of Blueprint 10.2 rather than authored as a
separate checklist, so it cannot drift from the workflow it protects (ADR-004
4.13). The derivation is re-computed from the state machines by test; the rules
layer states the result rather than importing ``state`` to compute it.

**The Checkpoint 6 gate (ADR-004 4.12):** the Kernel may not operate against
Foundation v1 while any of these lacks enforcement — that is, until this set is
a subset of ``IMPLEMENTED_CONDITIONS | SATISFIED_BY_DOMAIN_INVARIANT``.

The gate was **expected to fail at the end of Checkpoint 3, by design**: 8 of 24
were covered, and it was recorded as a blocking precondition on Checkpoint 6
rather than as untracked debt. **Checkpoint 6 closes it.** Twenty-one of the
twenty-four are enforced by a registered rule and two by a proven domain
invariant.

``TASKS_INSTANTIATED`` is the one entry that is required and has no rule, and it
is the one the Transition Runner discharges by construction (ADR-007 7.5): it
performs the instantiation inside the transaction and asserts the outcome it has
just produced. The gate check accounts for it explicitly rather than by
pretending a rule exists.
"""

_CLASSIFICATION: tuple[tuple[str, frozenset[TransitionCondition]], ...] = (
    ("IMPLEMENTED_CONDITIONS", IMPLEMENTED_CONDITIONS),
    ("PENDING_RULE_EXPANSION", PENDING_RULE_EXPANSION),
    ("SATISFIED_BY_DOMAIN_INVARIANT", SATISFIED_BY_DOMAIN_INVARIANT),
    ("BLOCKED_CONDITIONS", BLOCKED_CONDITIONS),
)


def condition_classification(condition: TransitionCondition) -> str:
    """Returns the name of the classification set ``condition`` belongs to."""
    for name, members in _CLASSIFICATION:
        if condition in members:
            return name
    raise RuleDefinitionError(f"Condition {condition} is not classified")


def _validate_classification() -> None:
    """Verifies the four sets partition the condition vocabulary.

    Union complete and pairwise disjoint: no condition can be silently
    unenforced, and no rule may introduce a condition the architecture never
    declared. Checked at import so a mistake cannot survive to runtime.
    """
    vocabulary = frozenset(TransitionCondition)
    classified: set[TransitionCondition] = set()
    for index, (name, members) in enumerate(_CLASSIFICATION):
        undeclared = sorted(members - vocabulary)
        if undeclared:
            raise RuleDefinitionError(f"{name} contains undeclared conditions: {undeclared}")
        for other_name, other in _CLASSIFICATION[index + 1 :]:
            overlap = sorted(members & other)
            if overlap:
                raise RuleDefinitionError(f"{name} and {other_name} both classify: {overlap}")
        classified |= members

    unclassified = sorted(vocabulary - classified)
    if unclassified:
        raise RuleDefinitionError(f"Conditions are classified by no registry set: {unclassified}")


_validate_classification()
