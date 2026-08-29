"""Stable machine vocabulary for the Rule Engine (ADR-004 4.3, 4.5).

Three closed vocabularies are declared here:

- :class:`RuleId` identifies **which rule** produced a result.
- :class:`RuleCode` identifies **which failure** occurred. One rule may emit
  several distinct codes.
- :class:`RuleStage` fixes the OS-owned evaluation order.

Every value is written out explicitly. Nothing is derived from a class name, so
renaming a rule class can never silently rename its machine contract. Both
vocabularies are pinned by test, which makes a rename a deliberate, reviewed
breaking change rather than an accident.
"""

from enum import IntEnum, StrEnum

__all__ = ["RuleCode", "RuleId", "RuleStage"]


class RuleStage(IntEnum):
    """The fixed, OS-owned evaluation stages (ADR-004 4.3).

    Order is a property of the code, never of any input. Agents never choose
    rule ordering and runtime configuration never reorders rules.

    ``STATE_TRANSITION`` is declared and **empty in Foundation v1**: structural
    transition validity belongs to the state machine, not to a rule. The slot is
    reserved so the approved order never has to be renumbered.
    """

    ACTOR_AUTHORITY = 1
    STATE_TRANSITION = 2
    PLAN_DEPENDENCY = 3
    EVIDENCE = 4
    ACCEPTANCE = 5


class RuleId(StrEnum):
    """Stable identifiers of the rules registered with the OS."""

    WORKER_CAPABILITY_MATCHES = "worker_capability_matches"
    DEPENDENCIES_ACCEPTED = "dependencies_accepted"
    SYSTEM_EVIDENCE_REQUIRED = "system_evidence_required"
    ALL_TASKS_ACCEPTED = "all_tasks_accepted"
    QA_FINAL_PASS_RECORDED = "qa_final_pass_recorded"
    QA_IN_SCOPE_ZERO_DEFECTS = "qa_in_scope_zero_defects"


class RuleCode(StrEnum):
    """Stable failure codes. This is the contract software depends on.

    A ``message`` explains a failure to a human; a ``code`` is what another
    program branches on. Free-form error strings are never the machine contract.
    """

    # worker_capability_matches
    WORKER_CAPABILITY_MISMATCH = "WORKER_CAPABILITY_MISMATCH"

    # dependencies_accepted
    DEPENDENCY_NOT_ACCEPTED = "DEPENDENCY_NOT_ACCEPTED"
    DEPENDENCY_FACTS_MISSING = "DEPENDENCY_FACTS_MISSING"

    # system_evidence_required
    MISSING_SYSTEM_EVIDENCE = "MISSING_SYSTEM_EVIDENCE"
    EVIDENCE_STANDARD_UNDEFINED = "EVIDENCE_STANDARD_UNDEFINED"

    # all_tasks_accepted
    TASK_NOT_ACCEPTED = "TASK_NOT_ACCEPTED"
    NO_TASKS_RECORDED = "NO_TASKS_RECORDED"

    # qa_final_pass_recorded
    MISSING_QA_FINAL_PASS = "MISSING_QA_FINAL_PASS"
    INVALID_QA_FINAL_PASS = "INVALID_QA_FINAL_PASS"

    # qa_in_scope_zero_defects
    UNRESOLVED_IN_SCOPE_DEFECT = "UNRESOLVED_IN_SCOPE_DEFECT"
    DEFECT_SCOPE_UNRESOLVED = "DEFECT_SCOPE_UNRESOLVED"
