"""Unit tests for the deterministic lifecycle state machines.

Every transition asserted here is transcribed from Implementation Blueprint
sections 5.1-5.3 and Design Session 009.
"""

from enum import StrEnum

import pytest

from ai_engineering_os.domain.enums import (
    ActorRole,
    FeatureStatus,
    Initiator,
    PlanStatus,
    SystemActor,
    TaskStatus,
    WorkPackageStatus,
)
from ai_engineering_os.domain.errors import StateMachineDefinitionError
from ai_engineering_os.state import (
    FEATURE_PLAN_STATE_MACHINE,
    FEATURE_STATE_MACHINE,
    TASK_STATE_MACHINE,
    WORK_PACKAGE_STATE_MACHINE,
    StateMachine,
    TransitionCondition,
    TransitionDefinition,
    TransitionRejectedError,
    TransitionRejectionCode,
)

ALL_MACHINES = [
    FEATURE_STATE_MACHINE,
    FEATURE_PLAN_STATE_MACHINE,
    TASK_STATE_MACHINE,
    WORK_PACKAGE_STATE_MACHINE,
]


# --------------------------------------------------------------------------
# Feature lifecycle (Blueprint 5.1)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_state", "to_state", "initiator"),
    [
        (FeatureStatus.DRAFT, FeatureStatus.PLANNED, ActorRole.COORDINATOR),
        (FeatureStatus.PLANNED, FeatureStatus.IN_PROGRESS, ActorRole.COORDINATOR),
        (FeatureStatus.IN_PROGRESS, FeatureStatus.IN_VALIDATION, ActorRole.COORDINATOR),
        (FeatureStatus.IN_PROGRESS, FeatureStatus.IN_VALIDATION, SystemActor.OS),
        (FeatureStatus.IN_VALIDATION, FeatureStatus.ACCEPTED, ActorRole.COORDINATOR),
        (FeatureStatus.IN_VALIDATION, FeatureStatus.IN_PROGRESS, ActorRole.COORDINATOR),
        (FeatureStatus.IN_VALIDATION, FeatureStatus.IN_PROGRESS, ActorRole.QA),
    ],
)
def test_valid_feature_transitions_are_allowed(
    from_state: FeatureStatus, to_state: FeatureStatus, initiator: Initiator
) -> None:
    """Verifies each Feature transition declared by Blueprint 5.1 is permitted."""
    evaluation = FEATURE_STATE_MACHINE.evaluate(from_state, to_state, initiator)
    assert evaluation.is_allowed
    assert evaluation.rejections == ()


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (FeatureStatus.DRAFT, FeatureStatus.ACCEPTED),
        (FeatureStatus.DRAFT, FeatureStatus.IN_PROGRESS),
        (FeatureStatus.PLANNED, FeatureStatus.ACCEPTED),
        (FeatureStatus.IN_PROGRESS, FeatureStatus.ACCEPTED),
        (FeatureStatus.IN_PROGRESS, FeatureStatus.DRAFT),
        (FeatureStatus.PLANNED, FeatureStatus.DRAFT),
    ],
)
def test_undefined_feature_transitions_are_rejected(
    from_state: FeatureStatus, to_state: FeatureStatus
) -> None:
    """Verifies Feature shortcuts and reversals are deterministically rejected."""
    evaluation = FEATURE_STATE_MACHINE.evaluate(from_state, to_state, ActorRole.COORDINATOR)
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNDEFINED_TRANSITION,)


def test_feature_acceptance_requires_the_coordinator() -> None:
    """Verifies only the Coordinator may accept a Feature (Design Session 004)."""
    evaluation = FEATURE_STATE_MACHINE.evaluate(
        FeatureStatus.IN_VALIDATION, FeatureStatus.ACCEPTED, ActorRole.QA
    )
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNAUTHORIZED_INITIATOR,)
    assert evaluation.rejections[0].allowed_initiators == ("COORDINATOR",)


def test_feature_acceptance_declares_its_os_validation_requirements() -> None:
    """Verifies the acceptance gate declares the conditions Checkpoint 3 must evaluate."""
    evaluation = FEATURE_STATE_MACHINE.evaluate(
        FeatureStatus.IN_VALIDATION, FeatureStatus.ACCEPTED, ActorRole.COORDINATOR
    )
    assert evaluation.required_conditions == frozenset(
        {
            TransitionCondition.ALL_TASKS_ACCEPTED,
            TransitionCondition.QA_FINAL_PASS_RECORDED,
            TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS,
            TransitionCondition.MANDATORY_EVIDENCE_PRESENT,
        }
    )


def test_accepted_feature_is_terminal() -> None:
    """Verifies ACCEPTED -> IN_PROGRESS fails because ACCEPTED is terminal."""
    evaluation = FEATURE_STATE_MACHINE.evaluate(
        FeatureStatus.ACCEPTED, FeatureStatus.IN_PROGRESS, ActorRole.COORDINATOR
    )
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.TERMINAL_STATE,)
    assert FEATURE_STATE_MACHINE.terminal_states == frozenset({FeatureStatus.ACCEPTED})


# --------------------------------------------------------------------------
# Task lifecycle (Blueprint 5.2)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_state", "to_state", "initiator"),
    [
        (TaskStatus.CREATED, TaskStatus.PENDING_DEPENDENCIES, SystemActor.OS),
        (TaskStatus.CREATED, TaskStatus.READY, SystemActor.OS),
        (TaskStatus.PENDING_DEPENDENCIES, TaskStatus.READY, SystemActor.OS),
        (TaskStatus.READY, TaskStatus.ASSIGNED, ActorRole.COORDINATOR),
        (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, ActorRole.WORKER),
        (TaskStatus.IN_PROGRESS, TaskStatus.SUBMITTED, ActorRole.WORKER),
        (TaskStatus.SUBMITTED, TaskStatus.IN_REVIEW, SystemActor.OS),
        (TaskStatus.IN_REVIEW, TaskStatus.IN_QA, ActorRole.REVIEWER),
        (TaskStatus.IN_REVIEW, TaskStatus.REVISION_REQUIRED, ActorRole.REVIEWER),
        (TaskStatus.IN_QA, TaskStatus.ACCEPTED, ActorRole.QA),
        (TaskStatus.IN_QA, TaskStatus.REVISION_REQUIRED, ActorRole.QA),
        (TaskStatus.IN_QA, TaskStatus.REVISION_REQUIRED, ActorRole.COORDINATOR),
        (TaskStatus.REVISION_REQUIRED, TaskStatus.IN_PROGRESS, ActorRole.WORKER),
    ],
)
def test_valid_task_transitions_are_allowed(
    from_state: TaskStatus, to_state: TaskStatus, initiator: Initiator
) -> None:
    """Verifies each Task transition declared by Blueprint 5.2 is permitted."""
    assert TASK_STATE_MACHINE.can_transition(from_state, to_state, initiator)


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (TaskStatus.CREATED, TaskStatus.ACCEPTED),
        (TaskStatus.CREATED, TaskStatus.IN_PROGRESS),
        (TaskStatus.CREATED, TaskStatus.SUBMITTED),
        (TaskStatus.READY, TaskStatus.IN_PROGRESS),
        (TaskStatus.ASSIGNED, TaskStatus.SUBMITTED),
        (TaskStatus.IN_PROGRESS, TaskStatus.IN_QA),
        (TaskStatus.SUBMITTED, TaskStatus.ACCEPTED),
        (TaskStatus.IN_REVIEW, TaskStatus.ACCEPTED),
        (TaskStatus.REVISION_REQUIRED, TaskStatus.SUBMITTED),
        (TaskStatus.PENDING_DEPENDENCIES, TaskStatus.ASSIGNED),
    ],
)
def test_task_shortcuts_are_rejected(from_state: TaskStatus, to_state: TaskStatus) -> None:
    """Verifies no Task may skip an independent verification stage (ADR-001)."""
    evaluation = TASK_STATE_MACHINE.evaluate(from_state, to_state, SystemActor.OS)
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNDEFINED_TRANSITION,)


def test_created_to_accepted_is_rejected_with_a_structured_explanation() -> None:
    """Verifies the canonical invalid Task transition explains itself."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.CREATED, TaskStatus.ACCEPTED, ActorRole.WORKER
    )
    assert not evaluation.is_allowed
    rejection = evaluation.rejections[0]
    assert rejection.code is TransitionRejectionCode.UNDEFINED_TRANSITION
    assert rejection.entity == "Task"
    assert rejection.from_state == TaskStatus.CREATED
    assert rejection.to_state == TaskStatus.ACCEPTED
    assert rejection.allowed_targets == ("PENDING_DEPENDENCIES", "READY")
    assert "no transition" in rejection.message


def test_accepted_task_cannot_reopen() -> None:
    """Verifies ACCEPTED -> IN_PROGRESS fails because ACCEPTED is terminal."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.ACCEPTED, TaskStatus.IN_PROGRESS, ActorRole.WORKER
    )
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.TERMINAL_STATE,)


def test_worker_cannot_accept_its_own_task() -> None:
    """Verifies ADR-001: the agent performing work never completes it."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.IN_QA, TaskStatus.ACCEPTED, ActorRole.WORKER
    )
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNAUTHORIZED_INITIATOR,)
    assert evaluation.rejections[0].allowed_initiators == ("QA",)


def test_worker_cannot_review_its_own_submission() -> None:
    """Verifies only the Reviewer may move a Task out of IN_REVIEW."""
    for target in (TaskStatus.IN_QA, TaskStatus.REVISION_REQUIRED):
        evaluation = TASK_STATE_MACHINE.evaluate(TaskStatus.IN_REVIEW, target, ActorRole.WORKER)
        assert not evaluation.is_allowed
        assert evaluation.rejection_codes == (TransitionRejectionCode.UNAUTHORIZED_INITIATOR,)


def test_coordinator_cannot_start_work_on_behalf_of_a_worker() -> None:
    """Verifies the Coordinator never performs implementation (Design Session 007)."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS, ActorRole.COORDINATOR
    )
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNAUTHORIZED_INITIATOR,)


def test_task_submission_declares_mandatory_evidence_conditions() -> None:
    """Verifies IN_PROGRESS -> SUBMITTED declares its Blueprint 5.2 requirements."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.IN_PROGRESS, TaskStatus.SUBMITTED, ActorRole.WORKER
    )
    assert evaluation.is_allowed
    assert evaluation.required_conditions == frozenset(
        {
            TransitionCondition.WORK_PACKAGE_PRESENT,
            TransitionCondition.CLAIMS_DEFINED,
            TransitionCondition.MANDATORY_SYSTEM_EVIDENCE_ATTACHED,
            TransitionCondition.VERIFICATION_GUIDE_PRESENT,
        }
    )


def test_rework_path_requires_an_incremented_revision() -> None:
    """Verifies REVISION_REQUIRED -> IN_PROGRESS declares the additive revision rule."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.REVISION_REQUIRED, TaskStatus.IN_PROGRESS, ActorRole.WORKER
    )
    assert evaluation.required_conditions == frozenset(
        {TransitionCondition.INCREMENTED_REVISION_CREATED}
    )


# --------------------------------------------------------------------------
# Feature Plan lifecycle (Design Session 009)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_state", "to_state", "initiator"),
    [
        (PlanStatus.DRAFT, PlanStatus.READY, ActorRole.COORDINATOR),
        (PlanStatus.READY, PlanStatus.ACTIVE, ActorRole.COORDINATOR),
        (PlanStatus.ACTIVE, PlanStatus.COMPLETED, ActorRole.COORDINATOR),
        (PlanStatus.ACTIVE, PlanStatus.COMPLETED, SystemActor.OS),
        (PlanStatus.ACTIVE, PlanStatus.SUPERSEDED, ActorRole.COORDINATOR),
    ],
)
def test_valid_plan_transitions_are_allowed(
    from_state: PlanStatus, to_state: PlanStatus, initiator: Initiator
) -> None:
    """Verifies the Feature Plan lifecycle from Design Session 009."""
    assert FEATURE_PLAN_STATE_MACHINE.can_transition(from_state, to_state, initiator)


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (PlanStatus.DRAFT, PlanStatus.ACTIVE),
        (PlanStatus.DRAFT, PlanStatus.COMPLETED),
        (PlanStatus.READY, PlanStatus.COMPLETED),
        (PlanStatus.ACTIVE, PlanStatus.DRAFT),
    ],
)
def test_invalid_plan_transitions_are_rejected(
    from_state: PlanStatus, to_state: PlanStatus
) -> None:
    """Verifies a Feature Plan cannot skip readiness or activation."""
    evaluation = FEATURE_PLAN_STATE_MACHINE.evaluate(from_state, to_state, ActorRole.COORDINATOR)
    assert not evaluation.is_allowed


def test_completed_and_superseded_plans_are_terminal() -> None:
    """Verifies a plan revision preserves history rather than reopening a plan."""
    assert FEATURE_PLAN_STATE_MACHINE.terminal_states == frozenset(
        {PlanStatus.COMPLETED, PlanStatus.SUPERSEDED}
    )
    evaluation = FEATURE_PLAN_STATE_MACHINE.evaluate(
        PlanStatus.SUPERSEDED, PlanStatus.ACTIVE, ActorRole.COORDINATOR
    )
    assert evaluation.rejection_codes == (TransitionRejectionCode.TERMINAL_STATE,)


def test_only_the_coordinator_owns_the_plan() -> None:
    """Verifies Design Session 009: the Coordinator owns the Feature Plan."""
    evaluation = FEATURE_PLAN_STATE_MACHINE.evaluate(
        PlanStatus.DRAFT, PlanStatus.READY, ActorRole.WORKER
    )
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNAUTHORIZED_INITIATOR,)


# --------------------------------------------------------------------------
# Work Package lifecycle (Blueprint 5.3)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_state", "to_state", "initiator"),
    [
        (WorkPackageStatus.DRAFT, WorkPackageStatus.SUBMITTED, ActorRole.WORKER),
        (WorkPackageStatus.SUBMITTED, WorkPackageStatus.VALIDATED, SystemActor.OS),
        (WorkPackageStatus.VALIDATED, WorkPackageStatus.REVIEWED, SystemActor.OS),
        (WorkPackageStatus.REVIEWED, WorkPackageStatus.ACCEPTED, SystemActor.OS),
        (WorkPackageStatus.REVIEWED, WorkPackageStatus.REJECTED, SystemActor.OS),
    ],
)
def test_valid_work_package_transitions_are_allowed(
    from_state: WorkPackageStatus, to_state: WorkPackageStatus, initiator: Initiator
) -> None:
    """Verifies the Work Package lifecycle from Blueprint 5.3."""
    assert WORK_PACKAGE_STATE_MACHINE.can_transition(from_state, to_state, initiator)


@pytest.mark.parametrize(
    ("from_state", "to_state"),
    [
        (WorkPackageStatus.SUBMITTED, WorkPackageStatus.DRAFT),
        (WorkPackageStatus.DRAFT, WorkPackageStatus.ACCEPTED),
        (WorkPackageStatus.SUBMITTED, WorkPackageStatus.REVIEWED),
        (WorkPackageStatus.VALIDATED, WorkPackageStatus.ACCEPTED),
    ],
)
def test_invalid_work_package_transitions_are_rejected(
    from_state: WorkPackageStatus, to_state: WorkPackageStatus
) -> None:
    """Verifies a submitted Work Package can never return to editable draft data."""
    evaluation = WORK_PACKAGE_STATE_MACHINE.evaluate(from_state, to_state, ActorRole.WORKER)
    assert not evaluation.is_allowed


def test_only_the_os_validates_a_submitted_work_package() -> None:
    """Verifies Design Session 005 Stage 1 validation belongs to the OS."""
    evaluation = WORK_PACKAGE_STATE_MACHINE.evaluate(
        WorkPackageStatus.SUBMITTED, WorkPackageStatus.VALIDATED, ActorRole.WORKER
    )
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNAUTHORIZED_INITIATOR,)
    assert evaluation.rejections[0].allowed_initiators == ("OS",)


OS_PROJECTED_WORK_PACKAGE_EDGES = [
    (WorkPackageStatus.SUBMITTED, WorkPackageStatus.VALIDATED),
    (WorkPackageStatus.VALIDATED, WorkPackageStatus.REVIEWED),
    (WorkPackageStatus.REVIEWED, WorkPackageStatus.ACCEPTED),
    (WorkPackageStatus.REVIEWED, WorkPackageStatus.REJECTED),
]


@pytest.mark.parametrize(("from_state", "to_state"), OS_PROJECTED_WORK_PACKAGE_EDGES)
@pytest.mark.parametrize(
    "role", [ActorRole.WORKER, ActorRole.REVIEWER, ActorRole.QA, ActorRole.COORDINATOR]
)
def test_no_actor_role_drives_work_package_state_after_submission(
    from_state: WorkPackageStatus, to_state: WorkPackageStatus, role: ActorRole
) -> None:
    """Verifies ADR-003 3.5: after submission, Work Package state is an OS projection.

    Reviewer, QA, and Coordinator act at the Task level. They hold no independent
    authority over Work Package state.
    """
    evaluation = WORK_PACKAGE_STATE_MACHINE.evaluate(from_state, to_state, role)
    assert not evaluation.is_allowed
    assert evaluation.rejection_codes == (TransitionRejectionCode.UNAUTHORIZED_INITIATOR,)
    assert evaluation.rejections[0].allowed_initiators == ("OS",)


@pytest.mark.parametrize(("from_state", "to_state"), OS_PROJECTED_WORK_PACKAGE_EDGES)
def test_os_drives_every_projected_work_package_edge(
    from_state: WorkPackageStatus, to_state: WorkPackageStatus
) -> None:
    """Verifies the OS is the sole initiator of every projected transition."""
    assert WORK_PACKAGE_STATE_MACHINE.can_transition(from_state, to_state, SystemActor.OS)


def test_only_the_worker_submits_a_work_package() -> None:
    """Verifies the single actor-requested Work Package transition stays with the Worker."""
    assert WORK_PACKAGE_STATE_MACHINE.allowed_initiators(
        WorkPackageStatus.DRAFT, WorkPackageStatus.SUBMITTED
    ) == frozenset({ActorRole.WORKER})


def test_accepted_and_rejected_work_packages_are_terminal() -> None:
    """Verifies the Work Package outcome states define no outgoing transition."""
    assert WORK_PACKAGE_STATE_MACHINE.terminal_states == frozenset(
        {WorkPackageStatus.ACCEPTED, WorkPackageStatus.REJECTED}
    )


# --------------------------------------------------------------------------
# Generic evaluator behaviour
# --------------------------------------------------------------------------


@pytest.mark.parametrize("machine", ALL_MACHINES, ids=lambda m: m.entity)
def test_self_transitions_are_never_defined(machine: StateMachine[StrEnum]) -> None:
    """Verifies no lifecycle declares a no-op transition onto itself."""
    for state in machine.states:
        assert machine.definition(state, state) is None


@pytest.mark.parametrize("machine", ALL_MACHINES, ids=lambda m: m.entity)
def test_every_state_participates_in_the_graph(machine: StateMachine[StrEnum]) -> None:
    """Verifies no lifecycle state is unreachable or undeclared."""
    referenced = {t.from_state for t in machine.transitions} | {
        t.to_state for t in machine.transitions
    }
    assert referenced == machine.states


@pytest.mark.parametrize("machine", ALL_MACHINES, ids=lambda m: m.entity)
def test_initial_state_has_no_inbound_transition(machine: StateMachine[StrEnum]) -> None:
    """Verifies the initial lifecycle state is never re-entered."""
    assert all(t.to_state != machine.initial_state for t in machine.transitions)


@pytest.mark.parametrize("machine", ALL_MACHINES, ids=lambda m: m.entity)
def test_every_transition_declares_an_initiator(machine: StateMachine[StrEnum]) -> None:
    """Verifies authority is explicit: no transition is open to everyone."""
    for transition in machine.transitions:
        assert transition.allowed_initiators, (
            f"{machine.entity} {transition.from_state} -> {transition.to_state} "
            f"declares no allowed initiator"
        )


def test_rejected_evaluation_can_be_raised_as_a_structured_domain_error() -> None:
    """Verifies rejections surface as domain errors carrying the full evaluation."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.CREATED, TaskStatus.ACCEPTED, ActorRole.WORKER
    )
    with pytest.raises(TransitionRejectedError) as excinfo:
        evaluation.raise_if_rejected()
    assert excinfo.value.code == "TRANSITION_REJECTED"
    assert excinfo.value.evaluation is evaluation


def test_allowed_evaluation_does_not_raise() -> None:
    """Verifies a valid transition passes through raise_if_rejected untouched."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.IN_PROGRESS, TaskStatus.SUBMITTED, ActorRole.WORKER
    )
    evaluation.raise_if_rejected()


def test_duplicate_transition_declaration_is_rejected() -> None:
    """Verifies a state machine cannot declare the same edge twice."""
    with pytest.raises(StateMachineDefinitionError):
        StateMachine(
            entity="Broken",
            state_type=PlanStatus,
            initial_state=PlanStatus.DRAFT,
            transitions=(
                TransitionDefinition(
                    from_state=PlanStatus.DRAFT,
                    to_state=PlanStatus.READY,
                    allowed_initiators=frozenset({ActorRole.COORDINATOR}),
                ),
                TransitionDefinition(
                    from_state=PlanStatus.DRAFT,
                    to_state=PlanStatus.READY,
                    allowed_initiators=frozenset({ActorRole.BUILDER}),
                ),
            ),
        )


def test_self_transition_declaration_is_rejected() -> None:
    """Verifies a state machine cannot declare a self-transition."""
    with pytest.raises(StateMachineDefinitionError):
        StateMachine(
            entity="Broken",
            state_type=PlanStatus,
            initial_state=PlanStatus.DRAFT,
            transitions=(
                TransitionDefinition(
                    from_state=PlanStatus.DRAFT,
                    to_state=PlanStatus.DRAFT,
                    allowed_initiators=frozenset({ActorRole.COORDINATOR}),
                ),
            ),
        )


def test_undeclared_state_is_rejected() -> None:
    """Verifies a state machine cannot silently omit a declared lifecycle state."""
    with pytest.raises(StateMachineDefinitionError):
        StateMachine(
            entity="Broken",
            state_type=PlanStatus,
            initial_state=PlanStatus.DRAFT,
            transitions=(
                TransitionDefinition(
                    from_state=PlanStatus.DRAFT,
                    to_state=PlanStatus.READY,
                    allowed_initiators=frozenset({ActorRole.COORDINATOR}),
                ),
            ),
        )


def test_evaluation_reports_current_and_requested_state() -> None:
    """Verifies an evaluation answers all four required transition questions."""
    evaluation = TASK_STATE_MACHINE.evaluate(
        TaskStatus.READY, TaskStatus.ASSIGNED, ActorRole.COORDINATOR
    )
    assert evaluation.entity == "Task"
    assert evaluation.from_state is TaskStatus.READY
    assert evaluation.to_state is TaskStatus.ASSIGNED
    assert evaluation.initiator is ActorRole.COORDINATOR
    assert evaluation.is_allowed is True
