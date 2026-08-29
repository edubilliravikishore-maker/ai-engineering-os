"""Task lifecycle state machine (Implementation Blueprint 5.2)."""

from ai_engineering_os.domain.enums import ActorRole, SystemActor, TaskStatus
from ai_engineering_os.state.machine import (
    StateMachine,
    TransitionCondition,
    TransitionDefinition,
)

__all__ = ["TASK_STATE_MACHINE"]

TASK_STATE_MACHINE: StateMachine[TaskStatus] = StateMachine(
    entity="Task",
    state_type=TaskStatus,
    initial_state=TaskStatus.CREATED,
    transitions=(
        TransitionDefinition(
            from_state=TaskStatus.CREATED,
            to_state=TaskStatus.PENDING_DEPENDENCIES,
            allowed_initiators=frozenset({SystemActor.OS}),
            required_conditions=frozenset({TransitionCondition.TASK_HAS_DEPENDENCIES}),
        ),
        # ADR-003 3.12 / ADR-004 4.8: `-> READY` is the single execution
        # authorization gate. The ORIGINATING_PLAN_ACTIVE *rule* is deferred to
        # Checkpoint 6; the condition is declared here.
        TransitionDefinition(
            from_state=TaskStatus.CREATED,
            to_state=TaskStatus.READY,
            allowed_initiators=frozenset({SystemActor.OS}),
            required_conditions=frozenset(
                {
                    TransitionCondition.DEPENDENCIES_ACCEPTED,
                    TransitionCondition.ORIGINATING_PLAN_ACTIVE,
                }
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.PENDING_DEPENDENCIES,
            to_state=TaskStatus.READY,
            allowed_initiators=frozenset({SystemActor.OS}),
            required_conditions=frozenset(
                {
                    TransitionCondition.DEPENDENCIES_ACCEPTED,
                    TransitionCondition.ORIGINATING_PLAN_ACTIVE,
                }
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.READY,
            to_state=TaskStatus.ASSIGNED,
            allowed_initiators=frozenset({ActorRole.COORDINATOR}),
            required_conditions=frozenset(
                {
                    TransitionCondition.WORKER_IS_ACTIVE,
                    TransitionCondition.WORKER_CAPABILITY_MATCHES,
                }
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.ASSIGNED,
            to_state=TaskStatus.IN_PROGRESS,
            allowed_initiators=frozenset({ActorRole.WORKER}),
            required_conditions=frozenset({TransitionCondition.REQUESTER_IS_ASSIGNED_WORKER}),
        ),
        TransitionDefinition(
            from_state=TaskStatus.IN_PROGRESS,
            to_state=TaskStatus.SUBMITTED,
            allowed_initiators=frozenset({ActorRole.WORKER}),
            required_conditions=frozenset(
                {
                    TransitionCondition.WORK_PACKAGE_PRESENT,
                    TransitionCondition.CLAIMS_DEFINED,
                    TransitionCondition.MANDATORY_SYSTEM_EVIDENCE_ATTACHED,
                    TransitionCondition.VERIFICATION_GUIDE_PRESENT,
                }
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.SUBMITTED,
            to_state=TaskStatus.IN_REVIEW,
            allowed_initiators=frozenset({SystemActor.OS}),
            required_conditions=frozenset({TransitionCondition.REVIEWER_ASSIGNED}),
        ),
        TransitionDefinition(
            from_state=TaskStatus.IN_REVIEW,
            to_state=TaskStatus.IN_QA,
            allowed_initiators=frozenset({ActorRole.REVIEWER}),
            required_conditions=frozenset(
                {
                    TransitionCondition.REVIEW_DECISION_APPROVED,
                    TransitionCondition.REVIEW_NOTES_PRESENT,
                }
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.IN_REVIEW,
            to_state=TaskStatus.REVISION_REQUIRED,
            allowed_initiators=frozenset({ActorRole.REVIEWER}),
            required_conditions=frozenset(
                {
                    TransitionCondition.REVIEW_DECISION_CHANGES_REQUESTED,
                    TransitionCondition.REVIEW_FEEDBACK_PRESENT,
                }
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.IN_QA,
            to_state=TaskStatus.ACCEPTED,
            allowed_initiators=frozenset({ActorRole.QA}),
            required_conditions=frozenset(
                {
                    TransitionCondition.QA_REPORT_PASSED,
                    TransitionCondition.TEST_EXECUTION_EVIDENCE_PRESENT,
                }
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.IN_QA,
            to_state=TaskStatus.REVISION_REQUIRED,
            allowed_initiators=frozenset({ActorRole.QA, ActorRole.COORDINATOR}),
            required_conditions=frozenset(
                {TransitionCondition.QA_REPORT_FAILED, TransitionCondition.DEFECTS_DOCUMENTED}
            ),
        ),
        TransitionDefinition(
            from_state=TaskStatus.REVISION_REQUIRED,
            to_state=TaskStatus.IN_PROGRESS,
            allowed_initiators=frozenset({ActorRole.WORKER}),
            required_conditions=frozenset({TransitionCondition.INCREMENTED_REVISION_CREATED}),
        ),
    ),
)
"""CREATED -> (PENDING_DEPENDENCIES) -> READY -> ASSIGNED -> IN_PROGRESS ->
SUBMITTED -> IN_REVIEW -> IN_QA -> ACCEPTED, with the REVISION_REQUIRED rework
path re-entering IN_PROGRESS on a new Revision."""
