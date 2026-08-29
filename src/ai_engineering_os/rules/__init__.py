"""Deterministic rule and policy evaluation for AI Engineering OS.

This layer answers one question: *are the conditions a lifecycle edge declares
satisfied by these facts?* It depends only on the pure domain layer, performs no
I/O, and mutates nothing.

The three-way separation of concerns (ADR-004 4.7):

=========  =========================================================
Layer      Question it answers
=========  =========================================================
``state``  Is this transition structurally defined, and may this
           initiator request it?
``rules``  Are the conditions this edge declares satisfied by these
           facts?
``core``   Atomically validate, mutate state, record audit, publish
           event. *(Checkpoint 6.)*
=========  =========================================================

``rules`` deliberately does **not** depend on ``state``: both consume the
condition vocabulary the ``domain`` layer owns.
"""

from ai_engineering_os.rules.acceptance import (
    AllTasksAcceptedRule,
    QAFinalPassRecordedRule,
    QAInScopeZeroDefectsRule,
)
from ai_engineering_os.rules.authority import WorkerCapabilityMatchesRule
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.dependencies import DependenciesAcceptedRule
from ai_engineering_os.rules.engine import RuleEngine, evaluation_order
from ai_engineering_os.rules.evidence import (
    MANDATORY_SYSTEM_EVIDENCE,
    SystemEvidenceRequiredRule,
)
from ai_engineering_os.rules.registry import (
    BLOCKED_CONDITIONS,
    FOUNDATION_V1_REQUIRED_CONDITIONS,
    IMPLEMENTED_CONDITIONS,
    PENDING_RULE_EXPANSION,
    RULE_ENGINE,
    RULES,
    SATISFIED_BY_DOMAIN_INVARIANT,
    condition_classification,
)
from ai_engineering_os.rules.results import (
    RuleDetail,
    RuleEvaluation,
    RuleResult,
    RulesRejectedError,
    RuleStatus,
)

__all__ = [
    "BLOCKED_CONDITIONS",
    "FOUNDATION_V1_REQUIRED_CONDITIONS",
    "IMPLEMENTED_CONDITIONS",
    "MANDATORY_SYSTEM_EVIDENCE",
    "PENDING_RULE_EXPANSION",
    "RULES",
    "RULE_ENGINE",
    "SATISFIED_BY_DOMAIN_INVARIANT",
    "AllTasksAcceptedRule",
    "DependenciesAcceptedRule",
    "QAFinalPassRecordedRule",
    "QAInScopeZeroDefectsRule",
    "Rule",
    "RuleCode",
    "RuleContext",
    "RuleDetail",
    "RuleEngine",
    "RuleEvaluation",
    "RuleFact",
    "RuleId",
    "RuleResult",
    "RuleStage",
    "RuleStatus",
    "RulesRejectedError",
    "SystemEvidenceRequiredRule",
    "WorkerCapabilityMatchesRule",
    "condition_classification",
    "evaluation_order",
]
