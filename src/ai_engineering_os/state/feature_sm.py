"""Feature lifecycle state machine (Implementation Blueprint 5.1)."""

from ai_engineering_os.domain.enums import ActorRole, FeatureStatus, SystemActor
from ai_engineering_os.state.machine import (
    StateMachine,
    TransitionCondition,
    TransitionDefinition,
)

__all__ = ["FEATURE_STATE_MACHINE"]

FEATURE_STATE_MACHINE: StateMachine[FeatureStatus] = StateMachine(
    entity="Feature",
    state_type=FeatureStatus,
    initial_state=FeatureStatus.DRAFT,
    transitions=(
        TransitionDefinition(
            from_state=FeatureStatus.DRAFT,
            to_state=FeatureStatus.PLANNED,
            allowed_initiators=frozenset({ActorRole.COORDINATOR}),
            required_conditions=frozenset(
                {
                    TransitionCondition.FEATURE_PLAN_ATTACHED,
                    TransitionCondition.PLAN_HAS_TASK_DEFINITIONS,
                }
            ),
        ),
        TransitionDefinition(
            from_state=FeatureStatus.PLANNED,
            to_state=FeatureStatus.IN_PROGRESS,
            allowed_initiators=frozenset({ActorRole.COORDINATOR}),
            required_conditions=frozenset(
                {
                    TransitionCondition.PLAN_IS_READY,
                    TransitionCondition.TASKS_INSTANTIATED,
                    TransitionCondition.PLAN_DEPENDENCIES_VALID,
                }
            ),
        ),
        TransitionDefinition(
            from_state=FeatureStatus.IN_PROGRESS,
            to_state=FeatureStatus.IN_VALIDATION,
            allowed_initiators=frozenset({ActorRole.COORDINATOR, SystemActor.OS}),
            required_conditions=frozenset({TransitionCondition.ALL_IMPLEMENTATION_TASKS_ACCEPTED}),
        ),
        TransitionDefinition(
            from_state=FeatureStatus.IN_VALIDATION,
            to_state=FeatureStatus.IN_PROGRESS,
            allowed_initiators=frozenset({ActorRole.COORDINATOR, ActorRole.QA}),
            required_conditions=frozenset({TransitionCondition.QA_DEFECT_FINDINGS_RECORDED}),
        ),
        TransitionDefinition(
            from_state=FeatureStatus.IN_VALIDATION,
            to_state=FeatureStatus.ACCEPTED,
            allowed_initiators=frozenset({ActorRole.COORDINATOR}),
            required_conditions=frozenset(
                {
                    TransitionCondition.ALL_TASKS_ACCEPTED,
                    TransitionCondition.QA_FINAL_PASS_RECORDED,
                    TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS,
                    TransitionCondition.MANDATORY_EVIDENCE_PRESENT,
                }
            ),
        ),
    ),
)
"""DRAFT -> PLANNED -> IN_PROGRESS -> IN_VALIDATION -> ACCEPTED, with the
IN_VALIDATION -> IN_PROGRESS rework path for QA defect findings."""
