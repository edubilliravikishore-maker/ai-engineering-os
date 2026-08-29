"""Plan and dependency rules — evaluation stage 3 (ADR-004 4.3, 4.10).

Checkpoint 3 implements exactly one dependency rule. ``ORIGINATING_PLAN_ACTIVE``
is declared on both Task ``-> READY`` edges by ADR-004 4.8, but its **rule**
remains deferred to Checkpoint 6 (ADR-003 3.12). Declaring the condition without
its rule is deliberate: the engine reports it as unevaluated on every ``-> READY``
evaluation, which keeps the gap visible rather than silently satisfied.
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import TaskStatus
from ai_engineering_os.domain.identifiers import TaskId
from ai_engineering_os.domain.task import Task
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult

__all__ = ["DependenciesAcceptedRule"]


class DependenciesAcceptedRule(Rule):
    """Every declared prerequisite Task must have reached ``ACCEPTED``.

    Blueprint 5.2 gates ``CREATED`` / ``PENDING_DEPENDENCIES -> READY`` on all
    dependencies being accepted. A Task declaring no dependency satisfies this
    vacuously — that is what makes it eligible for ``CREATED -> READY``.

    **Unknown dependency facts fail closed.** If a declared dependency
    identifier resolves to no supplied Task, the OS cannot know whether it was
    accepted, so the rule rejects with ``DEPENDENCY_FACTS_MISSING`` rather than
    passing. An unresolvable prerequisite is exactly the case where a silent
    pass would let unverified work advance.
    """

    rule_id = RuleId.DEPENDENCIES_ACCEPTED
    condition = TransitionCondition.DEPENDENCIES_ACCEPTED
    stage = RuleStage.PLAN_DEPENDENCY
    required_facts = frozenset({RuleFact.TASK, RuleFact.FEATURE_TASKS, RuleFact.REFERENCED_TASKS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether every declared prerequisite Task is ACCEPTED."""
        task = context.require_task()
        known: dict[TaskId, Task] = {
            candidate.id: candidate
            for candidate in (*context.require_feature_tasks(), *context.require_referenced_tasks())
        }

        unresolved = tuple(
            dependency for dependency in task.dependencies if dependency not in known
        )
        if unresolved:
            return self.failed(
                RuleCode.DEPENDENCY_FACTS_MISSING,
                f"Task {task.id} declares {len(unresolved)} dependency identifier(s) that "
                f"resolve to no supplied Task, so acceptance cannot be determined",
                RuleDetail.of("unresolved_dependencies", unresolved),
                RuleDetail.of("task_id", [task.id]),
            )

        unaccepted = tuple(
            known[dependency]
            for dependency in task.dependencies
            if known[dependency].status is not TaskStatus.ACCEPTED
        )
        if unaccepted:
            return self.failed(
                RuleCode.DEPENDENCY_NOT_ACCEPTED,
                f"Task {task.id} depends on {len(unaccepted)} Task(s) that are not ACCEPTED",
                RuleDetail.of("unaccepted_dependencies", (t.id for t in unaccepted)),
                RuleDetail.of("unaccepted_dependency_statuses", (t.status for t in unaccepted)),
                RuleDetail.of("task_id", [task.id]),
            )

        return self.passed(
            f"All {len(task.dependencies)} declared dependencies of Task {task.id} are ACCEPTED"
        )
