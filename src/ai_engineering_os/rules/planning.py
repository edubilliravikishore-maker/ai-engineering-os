"""Plan and dependency rules — evaluation stage 3 (ADR-004 4.3, 4.10).

Four rules governing the two planning gates: Feature ``DRAFT -> PLANNED``,
Feature ``PLANNED -> IN_PROGRESS``, and the Task ``-> READY`` execution
authorization gate.

All four read ``feature_plans`` rather than a single optional plan. An empty
tuple is a **real finding** — no plan is attached — and the requester needs to
be told that, not to have the evaluation abort because a fact was absent.

``PLAN_DEPENDENCIES_VALID`` has no rule here and never will: ``FeaturePlan``
validates key uniqueness, dependency resolvability and acyclicity at
construction, so a rule for it could never fail (ADR-004 4.11).
"""

from collections.abc import Sequence

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import PlanStatus
from ai_engineering_os.domain.plan import FeaturePlan
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult

__all__ = [
    "FeaturePlanAttachedRule",
    "OriginatingPlanActiveRule",
    "PlanHasTaskDefinitionsRule",
    "PlanIsReadyRule",
]

_LIVE_PLAN_STATUSES: frozenset[PlanStatus] = frozenset(
    {PlanStatus.DRAFT, PlanStatus.READY, PlanStatus.ACTIVE}
)
"""Statuses in which a Plan still governs the Feature.

``COMPLETED`` and ``SUPERSEDED`` are history. A Feature whose only Plan is
superseded has no live plan, and saying it is planned would be false.
"""


def _live_plans(plans: Sequence[FeaturePlan], feature_id: object) -> tuple[FeaturePlan, ...]:
    """Returns the Feature's Plans that still govern it, newest revision first."""
    live = [
        plan
        for plan in plans
        if plan.feature_id == feature_id and plan.status in _LIVE_PLAN_STATUSES
    ]
    return tuple(sorted(live, key=lambda plan: plan.revision_number, reverse=True))


class FeaturePlanAttachedRule(Rule):
    """A Feature must carry a live Feature Plan before it can be planned.

    Blueprint 5.1 ``DRAFT -> PLANNED``. A superseded or completed Plan does not
    satisfy this: it records what was once intended, not what governs now.
    """

    rule_id = RuleId.FEATURE_PLAN_ATTACHED
    condition = TransitionCondition.FEATURE_PLAN_ATTACHED
    stage = RuleStage.PLAN_DEPENDENCY
    required_facts = frozenset({RuleFact.FEATURE, RuleFact.FEATURE_PLANS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether a live Feature Plan is attached to the Feature."""
        feature = context.require_feature()
        live = _live_plans(context.require_feature_plans(), feature.id)

        if not live:
            return self.failed(
                RuleCode.NO_FEATURE_PLAN_ATTACHED,
                f"Feature {feature.id} carries no live Feature Plan",
                RuleDetail.of("feature_id", [feature.id]),
                RuleDetail.of(
                    "plan_statuses",
                    (plan.status for plan in context.require_feature_plans()),
                ),
            )

        return self.passed(f"Feature {feature.id} carries {len(live)} live Feature Plan(s)")


class PlanHasTaskDefinitionsRule(Rule):
    """The Feature's live Plan must define at least one Task.

    Blueprint 5.1 ``DRAFT -> PLANNED``. A plan that defines no work is not a
    plan, and planning a Feature against one would produce a Feature that can
    never leave ``IN_PROGRESS``.

    Declares ``FEATURE_PLAN_ATTACHED`` as a prerequisite: with no plan attached
    there is nothing whose task definitions could be counted, and reporting
    "defines no tasks" for a Feature that has no plan at all would be a
    misleading verdict rather than a second finding.
    """

    rule_id = RuleId.PLAN_HAS_TASK_DEFINITIONS
    condition = TransitionCondition.PLAN_HAS_TASK_DEFINITIONS
    stage = RuleStage.PLAN_DEPENDENCY
    required_facts = frozenset({RuleFact.FEATURE, RuleFact.FEATURE_PLANS})
    requires = frozenset({RuleId.FEATURE_PLAN_ATTACHED})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the Feature's newest live Plan defines Tasks."""
        feature = context.require_feature()
        live = _live_plans(context.require_feature_plans(), feature.id)
        plan = live[0]

        if not plan.task_definitions:
            return self.failed(
                RuleCode.PLAN_DEFINES_NO_TASKS,
                f"Feature Plan {plan.id} defines no Task, so there is no work to plan",
                RuleDetail.of("feature_plan_id", [plan.id]),
                RuleDetail.of("feature_id", [feature.id]),
            )

        return self.passed(
            f"Feature Plan {plan.id} defines {len(plan.task_definitions)} Task definition(s)"
        )


class PlanIsReadyRule(Rule):
    """The Plan being executed must have reached ``READY`` or ``ACTIVE``.

    Blueprint 5.1 ``PLANNED -> IN_PROGRESS``. A ``DRAFT`` plan is still being
    written; instantiating Tasks from it would give execution authority to work
    nobody has finished planning (ADR-003 3.12).

    ``ACTIVE`` passes as well as ``READY`` so the check is idempotent: a
    re-evaluation after activation must not report that an executing plan is
    not ready.
    """

    rule_id = RuleId.PLAN_IS_READY
    condition = TransitionCondition.PLAN_IS_READY
    stage = RuleStage.PLAN_DEPENDENCY
    required_facts = frozenset({RuleFact.FEATURE, RuleFact.FEATURE_PLANS})
    requires = frozenset({RuleId.FEATURE_PLAN_ATTACHED})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the Feature's newest live Plan may be executed."""
        feature = context.require_feature()
        plan = _live_plans(context.require_feature_plans(), feature.id)[0]

        if plan.status not in (PlanStatus.READY, PlanStatus.ACTIVE):
            return self.failed(
                RuleCode.PLAN_NOT_READY,
                f"Feature Plan {plan.id} is {plan.status} and is not ready to execute",
                RuleDetail.of("feature_plan_id", [plan.id]),
                RuleDetail.of("plan_status", [plan.status]),
                RuleDetail.of("feature_id", [feature.id]),
            )

        return self.passed(f"Feature Plan {plan.id} is {plan.status} and may be executed")


class OriginatingPlanActiveRule(Rule):
    """A Task may only become READY while the Plan that produced it is ACTIVE.

    ADR-003 3.12 and ADR-004 4.8: existence confers no execution authority. A
    Task created under a ``DRAFT`` plan is a planning record, and a Task whose
    plan has been superseded must not start work the OS no longer intends.

    The Task carries ``feature_plan_id`` precisely so this is answerable. A Task
    whose originating Plan is not among the supplied Plans fails closed with its
    own code: the OS does not assume a plan it cannot see is active.
    """

    rule_id = RuleId.ORIGINATING_PLAN_ACTIVE
    condition = TransitionCondition.ORIGINATING_PLAN_ACTIVE
    stage = RuleStage.PLAN_DEPENDENCY
    required_facts = frozenset({RuleFact.TASK, RuleFact.FEATURE_PLANS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the Task's originating Plan is ACTIVE."""
        task = context.require_task()
        plans = {plan.id: plan for plan in context.require_feature_plans()}
        plan = plans.get(task.feature_plan_id)

        if plan is None:
            return self.failed(
                RuleCode.ORIGINATING_PLAN_NOT_SUPPLIED,
                f"Task {task.id} names Feature Plan {task.feature_plan_id}, which was not "
                f"supplied, so its status cannot be established",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("feature_plan_id", [task.feature_plan_id]),
            )

        if plan.status is not PlanStatus.ACTIVE:
            return self.failed(
                RuleCode.ORIGINATING_PLAN_NOT_ACTIVE,
                f"Task {task.id} originates from Feature Plan {plan.id}, which is "
                f"{plan.status} rather than ACTIVE",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("feature_plan_id", [plan.id]),
                RuleDetail.of("plan_status", [plan.status]),
            )

        return self.passed(f"Task {task.id} originates from ACTIVE Feature Plan {plan.id}")
