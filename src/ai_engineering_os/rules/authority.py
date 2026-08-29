"""Actor and authority rules — evaluation stage 1 (ADR-004 4.3, 4.10).

Checkpoint 3 implements exactly one authority rule. ``WORKER_IS_ACTIVE`` and
``REQUESTER_IS_ASSIGNED_WORKER`` are declared by the Task lifecycle and remain
in ``PENDING_RULE_EXPANSION``: they are computable today and deferred by scope
decision alone, never silently implemented here.
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult

__all__ = ["WorkerCapabilityMatchesRule"]


class WorkerCapabilityMatchesRule(Rule):
    """The Worker being assigned must possess the Task's required capability.

    Blueprint 5.2 ``READY -> ASSIGNED`` requires that the Worker "possesses
    matching capability". Capability is read from the Actor's declared
    capability set — the same semantics ``Actor.has_capability`` already
    enforces — never inferred from the request.

    This rule deliberately checks capability **only**. Whether the Worker is
    active is the separate ``WORKER_IS_ACTIVE`` condition, which has no rule
    yet; folding it in here would hide an unimplemented requirement inside an
    implemented one.
    """

    rule_id = RuleId.WORKER_CAPABILITY_MATCHES
    condition = TransitionCondition.WORKER_CAPABILITY_MATCHES
    stage = RuleStage.ACTOR_AUTHORITY
    required_facts = frozenset({RuleFact.CANDIDATE_WORKER, RuleFact.TASK})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the candidate Worker owns the Task's capability."""
        worker = context.require_candidate_worker()
        task = context.require_task()

        if worker.has_capability(task.capability):
            return self.passed(
                f"Worker {worker.id} declares the required capability {task.capability}"
            )

        return self.failed(
            RuleCode.WORKER_CAPABILITY_MISMATCH,
            f"Worker {worker.id} does not declare the capability {task.capability} "
            f"required by Task {task.id}",
            RuleDetail.of("required_capability", [task.capability]),
            RuleDetail.of("worker_capabilities", sorted(worker.capabilities)),
            RuleDetail.of("worker_id", [worker.id]),
            RuleDetail.of("task_id", [task.id]),
        )
