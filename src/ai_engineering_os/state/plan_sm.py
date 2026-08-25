"""Feature Plan lifecycle state machine (Design Session 009).

Design Session 009 records the plan lifecycle as
``DRAFT -> READY -> ACTIVE -> COMPLETED`` and requires that a plan is revised
into a new revision rather than being silently overwritten, which is the
``ACTIVE -> SUPERSEDED`` edge.
"""

from ai_engineering_os.domain.enums import ActorRole, PlanStatus, SystemActor
from ai_engineering_os.state.machine import StateMachine, TransitionDefinition

__all__ = ["FEATURE_PLAN_STATE_MACHINE"]

FEATURE_PLAN_STATE_MACHINE: StateMachine[PlanStatus] = StateMachine(
    entity="FeaturePlan",
    state_type=PlanStatus,
    initial_state=PlanStatus.DRAFT,
    transitions=(
        TransitionDefinition(
            from_state=PlanStatus.DRAFT,
            to_state=PlanStatus.READY,
            allowed_initiators=frozenset({ActorRole.COORDINATOR}),
        ),
        TransitionDefinition(
            from_state=PlanStatus.READY,
            to_state=PlanStatus.ACTIVE,
            allowed_initiators=frozenset({ActorRole.COORDINATOR}),
        ),
        TransitionDefinition(
            from_state=PlanStatus.ACTIVE,
            to_state=PlanStatus.COMPLETED,
            allowed_initiators=frozenset({ActorRole.COORDINATOR, SystemActor.OS}),
        ),
        TransitionDefinition(
            from_state=PlanStatus.ACTIVE,
            to_state=PlanStatus.SUPERSEDED,
            allowed_initiators=frozenset({ActorRole.COORDINATOR}),
        ),
    ),
)
"""DRAFT -> READY -> ACTIVE -> COMPLETED, or ACTIVE -> SUPERSEDED on revision."""
