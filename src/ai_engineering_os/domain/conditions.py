"""The named OS validation requirement vocabulary (ADR-004 4.7).

These are the "OS Validation Requirements" columns of Implementation Blueprint
sections 5.1 and 5.2, transcribed as identifiers.

The vocabulary is owned by the ``domain`` layer because two layers consume it
while answering different questions about the same named requirement:

```
              domain
             /      \\
         state      rules
```

- ``domain`` owns the named condition vocabulary.
- ``state`` declares which conditions govern each lifecycle edge.
- ``rules`` evaluates whether those conditions are satisfied by supplied facts.
- ``rules`` must not depend on ``state``.

Placing shared vocabulary in the layer both consumers depend on is the only
arrangement that satisfies the Blueprint section 3 dependency table without
duplicating the vocabulary, and a duplicated vocabulary is one that will drift.
"""

from enum import StrEnum

__all__ = ["TransitionCondition"]


class TransitionCondition(StrEnum):
    """Named OS validation requirements declared by a lifecycle transition.

    A condition is a *requirement*, not a rule. The ``state`` layer declares
    which conditions an edge requires; the ``rules`` layer evaluates them. A
    condition with no registered rule is reported as unevaluated rather than
    silently treated as satisfied (ADR-004 4.5).
    """

    # Feature lifecycle (Blueprint 5.1)
    FEATURE_PLAN_ATTACHED = "FEATURE_PLAN_ATTACHED"
    PLAN_HAS_TASK_DEFINITIONS = "PLAN_HAS_TASK_DEFINITIONS"
    PLAN_IS_READY = "PLAN_IS_READY"
    PLAN_DEPENDENCIES_VALID = "PLAN_DEPENDENCIES_VALID"
    TASKS_INSTANTIATED = "TASKS_INSTANTIATED"
    ALL_IMPLEMENTATION_TASKS_ACCEPTED = "ALL_IMPLEMENTATION_TASKS_ACCEPTED"
    ALL_TASKS_ACCEPTED = "ALL_TASKS_ACCEPTED"
    QA_FINAL_PASS_RECORDED = "QA_FINAL_PASS_RECORDED"
    ZERO_UNRESOLVED_IN_SCOPE_DEFECTS = "ZERO_UNRESOLVED_IN_SCOPE_DEFECTS"
    MANDATORY_EVIDENCE_PRESENT = "MANDATORY_EVIDENCE_PRESENT"
    QA_DEFECT_FINDINGS_RECORDED = "QA_DEFECT_FINDINGS_RECORDED"

    # Task lifecycle (Blueprint 5.2)
    TASK_HAS_DEPENDENCIES = "TASK_HAS_DEPENDENCIES"
    DEPENDENCIES_ACCEPTED = "DEPENDENCIES_ACCEPTED"
    ORIGINATING_PLAN_ACTIVE = "ORIGINATING_PLAN_ACTIVE"
    WORKER_IS_ACTIVE = "WORKER_IS_ACTIVE"
    WORKER_CAPABILITY_MATCHES = "WORKER_CAPABILITY_MATCHES"
    REQUESTER_IS_ASSIGNED_WORKER = "REQUESTER_IS_ASSIGNED_WORKER"
    WORK_PACKAGE_PRESENT = "WORK_PACKAGE_PRESENT"
    CLAIMS_DEFINED = "CLAIMS_DEFINED"
    MANDATORY_SYSTEM_EVIDENCE_ATTACHED = "MANDATORY_SYSTEM_EVIDENCE_ATTACHED"
    VERIFICATION_GUIDE_PRESENT = "VERIFICATION_GUIDE_PRESENT"
    REVIEWER_ASSIGNED = "REVIEWER_ASSIGNED"
    REVIEW_DECISION_APPROVED = "REVIEW_DECISION_APPROVED"
    REVIEW_NOTES_PRESENT = "REVIEW_NOTES_PRESENT"
    REVIEW_DECISION_CHANGES_REQUESTED = "REVIEW_DECISION_CHANGES_REQUESTED"
    REVIEW_FEEDBACK_PRESENT = "REVIEW_FEEDBACK_PRESENT"
    QA_REPORT_PASSED = "QA_REPORT_PASSED"
    TEST_EXECUTION_EVIDENCE_PRESENT = "TEST_EXECUTION_EVIDENCE_PRESENT"
    QA_REPORT_FAILED = "QA_REPORT_FAILED"
    DEFECTS_DOCUMENTED = "DEFECTS_DOCUMENTED"
    INCREMENTED_REVISION_CREATED = "INCREMENTED_REVISION_CREATED"
