"""Work Package lifecycle state machine (Implementation Blueprint 5.3, ADR-003 3.5).

The Work Package lifecycle uses a **single authority model**. The Worker submits
the Work Package; every subsequent state is an **OS projection** of the
corresponding Task lifecycle outcome.

Reviewer, QA, and Coordinator hold no independent authority over Work Package
state. They act at the Task level, and the OS maintains the projection. Keeping
authority defined in exactly one place prevents a second authority model from
competing with the Task state machine over the same real-world action.
"""

from ai_engineering_os.domain.enums import ActorRole, SystemActor, WorkPackageStatus
from ai_engineering_os.state.machine import StateMachine, TransitionDefinition

__all__ = ["WORK_PACKAGE_STATE_MACHINE"]

WORK_PACKAGE_STATE_MACHINE: StateMachine[WorkPackageStatus] = StateMachine(
    entity="WorkPackage",
    state_type=WorkPackageStatus,
    initial_state=WorkPackageStatus.DRAFT,
    transitions=(
        # Worker submits the Work Package: Task IN_PROGRESS -> SUBMITTED.
        TransitionDefinition(
            from_state=WorkPackageStatus.DRAFT,
            to_state=WorkPackageStatus.SUBMITTED,
            allowed_initiators=frozenset({ActorRole.WORKER}),
        ),
        # Projection of OS Stage 1 mandatory-evidence validation (Design Session 005).
        TransitionDefinition(
            from_state=WorkPackageStatus.SUBMITTED,
            to_state=WorkPackageStatus.VALIDATED,
            allowed_initiators=frozenset({SystemActor.OS}),
        ),
        # Projection of Task IN_REVIEW -> IN_QA / -> REVISION_REQUIRED.
        TransitionDefinition(
            from_state=WorkPackageStatus.VALIDATED,
            to_state=WorkPackageStatus.REVIEWED,
            allowed_initiators=frozenset({SystemActor.OS}),
        ),
        # Projection of Task IN_QA -> ACCEPTED.
        TransitionDefinition(
            from_state=WorkPackageStatus.REVIEWED,
            to_state=WorkPackageStatus.ACCEPTED,
            allowed_initiators=frozenset({SystemActor.OS}),
        ),
        # Projection of Task -> REVISION_REQUIRED.
        TransitionDefinition(
            from_state=WorkPackageStatus.REVIEWED,
            to_state=WorkPackageStatus.REJECTED,
            allowed_initiators=frozenset({SystemActor.OS}),
        ),
    ),
)
"""DRAFT -> SUBMITTED -> VALIDATED -> REVIEWED -> ACCEPTED / REJECTED.

Only DRAFT -> SUBMITTED is actor-requested; the rest are OS projections."""
