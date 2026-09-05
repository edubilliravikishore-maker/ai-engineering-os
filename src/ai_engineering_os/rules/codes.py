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
    WORKER_IS_ACTIVE = "worker_is_active"
    REQUESTER_IS_ASSIGNED_WORKER = "requester_is_assigned_worker"
    REVIEWER_ASSIGNED = "reviewer_assigned"
    FEATURE_PLAN_ATTACHED = "feature_plan_attached"
    PLAN_HAS_TASK_DEFINITIONS = "plan_has_task_definitions"
    PLAN_IS_READY = "plan_is_ready"
    ORIGINATING_PLAN_ACTIVE = "originating_plan_active"
    DEPENDENCIES_ACCEPTED = "dependencies_accepted"
    WORK_PACKAGE_PRESENT = "work_package_present"
    CLAIMS_DEFINED = "claims_defined"
    VERIFICATION_GUIDE_PRESENT = "verification_guide_present"
    SYSTEM_EVIDENCE_REQUIRED = "system_evidence_required"
    FEATURE_EVIDENCE_PRESENT = "feature_evidence_present"
    REVIEW_DECISION_APPROVED = "review_decision_approved"
    QA_REPORT_PASSED = "qa_report_passed"
    TEST_EXECUTION_EVIDENCE_PRESENT = "test_execution_evidence_present"
    IMPLEMENTATION_TASKS_ACCEPTED = "implementation_tasks_accepted"
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

    # worker_is_active
    WORKER_INACTIVE = "WORKER_INACTIVE"
    ACTOR_IS_NOT_A_WORKER = "ACTOR_IS_NOT_A_WORKER"

    # requester_is_assigned_worker
    REQUESTER_IS_NOT_THE_ASSIGNED_WORKER = "REQUESTER_IS_NOT_THE_ASSIGNED_WORKER"
    TASK_HAS_NO_ASSIGNED_WORKER = "TASK_HAS_NO_ASSIGNED_WORKER"

    # reviewer_assigned
    NO_REVIEWER_ROUTED = "NO_REVIEWER_ROUTED"
    REVIEWER_NOT_ELIGIBLE = "REVIEWER_NOT_ELIGIBLE"
    REVIEWER_CAPABILITY_MISMATCH = "REVIEWER_CAPABILITY_MISMATCH"
    REVIEWER_PERFORMED_THE_WORK = "REVIEWER_PERFORMED_THE_WORK"

    # feature_plan_attached
    NO_FEATURE_PLAN_ATTACHED = "NO_FEATURE_PLAN_ATTACHED"

    # plan_has_task_definitions
    PLAN_DEFINES_NO_TASKS = "PLAN_DEFINES_NO_TASKS"

    # plan_is_ready
    PLAN_NOT_READY = "PLAN_NOT_READY"

    # originating_plan_active
    ORIGINATING_PLAN_NOT_SUPPLIED = "ORIGINATING_PLAN_NOT_SUPPLIED"
    ORIGINATING_PLAN_NOT_ACTIVE = "ORIGINATING_PLAN_NOT_ACTIVE"

    # work_package_present / claims_defined / verification_guide_present
    NO_ACTIVE_REVISION = "NO_ACTIVE_REVISION"
    NO_WORK_PACKAGE_SUBMITTED = "NO_WORK_PACKAGE_SUBMITTED"
    NO_CLAIMS_DECLARED = "NO_CLAIMS_DECLARED"
    NO_VERIFICATION_GUIDE = "NO_VERIFICATION_GUIDE"

    # feature_evidence_present
    MISSING_FEATURE_EVIDENCE = "MISSING_FEATURE_EVIDENCE"

    # review_decision_approved
    NO_REVIEW_DECISION_RECORDED = "NO_REVIEW_DECISION_RECORDED"
    REVIEW_CHANGES_REQUESTED = "REVIEW_CHANGES_REQUESTED"

    # qa_report_passed
    NO_QA_REPORT_FOR_REVISION = "NO_QA_REPORT_FOR_REVISION"
    QA_REPORT_DID_NOT_PASS = "QA_REPORT_DID_NOT_PASS"

    # test_execution_evidence_present
    NO_TEST_RESULTS_RECORDED = "NO_TEST_RESULTS_RECORDED"
    NO_TEST_EXECUTION_EVIDENCE = "NO_TEST_EXECUTION_EVIDENCE"

    # implementation_tasks_accepted
    IMPLEMENTATION_TASK_NOT_ACCEPTED = "IMPLEMENTATION_TASK_NOT_ACCEPTED"
    NO_IMPLEMENTATION_TASKS_RECORDED = "NO_IMPLEMENTATION_TASKS_RECORDED"

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
