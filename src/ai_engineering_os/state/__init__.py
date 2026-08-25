"""Deterministic lifecycle state machines for AI Engineering OS.

This layer owns valid state graphs, transition definitions, and the transition
evaluator. It depends only on the pure domain layer and performs no I/O.
"""

from ai_engineering_os.state.feature_sm import FEATURE_STATE_MACHINE
from ai_engineering_os.state.machine import (
    StateMachine,
    TransitionCondition,
    TransitionDefinition,
    TransitionEvaluation,
    TransitionRejectedError,
    TransitionRejection,
    TransitionRejectionCode,
)
from ai_engineering_os.state.plan_sm import FEATURE_PLAN_STATE_MACHINE
from ai_engineering_os.state.task_sm import TASK_STATE_MACHINE
from ai_engineering_os.state.work_package_sm import WORK_PACKAGE_STATE_MACHINE

__all__ = [
    "FEATURE_PLAN_STATE_MACHINE",
    "FEATURE_STATE_MACHINE",
    "TASK_STATE_MACHINE",
    "WORK_PACKAGE_STATE_MACHINE",
    "StateMachine",
    "TransitionCondition",
    "TransitionDefinition",
    "TransitionEvaluation",
    "TransitionRejectedError",
    "TransitionRejection",
    "TransitionRejectionCode",
]
