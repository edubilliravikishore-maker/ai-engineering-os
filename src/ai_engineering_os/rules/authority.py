"""Actor and authority rules — evaluation stage 1 (ADR-004 4.3, 4.10).

Every rule here answers the same shape of question: *may this Actor do this?*
Authority never follows from the request itself, so each reads the Actor as a
supplied fact and compares it against what the Task records.

The three capability and identity rules were computable at Checkpoint 3 and
deferred by scope decision. ``REVIEWER_ASSIGNED`` was not: it needed the Builder
ruling of ADR-007 7.3 and the ``Task.reviewer_id`` that ruling created.
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import ActorRole
from ai_engineering_os.domain.task import work_authors
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult

__all__ = [
    "ReviewerAssignedRule",
    "RequesterIsAssignedWorkerRule",
    "WorkerCapabilityMatchesRule",
    "WorkerIsActiveRule",
]


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


class WorkerIsActiveRule(Rule):
    """The Worker being assigned must be an active Worker.

    Blueprint 5.2 ``READY -> ASSIGNED`` requires that the Worker "is active".
    Deliberately separate from ``WorkerCapabilityMatchesRule``: an inactive
    Worker and an unqualified one are different problems with different
    remedies, and reporting them together lets a Coordinator fix both in one
    pass rather than one reject cycle at a time.

    Role is checked here as well as activity. An Actor that is not a ``WORKER``
    cannot be an active Worker, and saying so precisely is more useful than
    reporting a capability mismatch for a Reviewer who was never eligible.
    """

    rule_id = RuleId.WORKER_IS_ACTIVE
    condition = TransitionCondition.WORKER_IS_ACTIVE
    stage = RuleStage.ACTOR_AUTHORITY
    required_facts = frozenset({RuleFact.CANDIDATE_WORKER})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the candidate is an active Worker."""
        worker = context.require_candidate_worker()

        if worker.role is not ActorRole.WORKER:
            return self.failed(
                RuleCode.ACTOR_IS_NOT_A_WORKER,
                f"Actor {worker.id} holds role {worker.role} and cannot be assigned work",
                RuleDetail.of("actor_id", [worker.id]),
                RuleDetail.of("actor_role", [worker.role]),
            )

        if not worker.is_active:
            return self.failed(
                RuleCode.WORKER_INACTIVE,
                f"Worker {worker.id} is not active and cannot be assigned work",
                RuleDetail.of("worker_id", [worker.id]),
            )

        return self.passed(f"Worker {worker.id} is active")


class RequesterIsAssignedWorkerRule(Rule):
    """Only the Worker a Task is assigned to may start it.

    Blueprint 5.2 ``ASSIGNED -> IN_PROGRESS``. The requester is a supplied fact,
    never read from the request being evaluated, so a caller cannot assert its
    own authority.
    """

    rule_id = RuleId.REQUESTER_IS_ASSIGNED_WORKER
    condition = TransitionCondition.REQUESTER_IS_ASSIGNED_WORKER
    stage = RuleStage.ACTOR_AUTHORITY
    required_facts = frozenset({RuleFact.REQUESTING_ACTOR, RuleFact.TASK})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the requester is the Task's assigned Worker."""
        requester = context.require_requesting_actor()
        task = context.require_task()

        if task.assigned_worker_id is None:
            return self.failed(
                RuleCode.TASK_HAS_NO_ASSIGNED_WORKER,
                f"Task {task.id} records no assigned Worker, so no requester can be it",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("requester_id", [requester.id]),
            )

        if not task.is_assigned_to(requester.id):
            return self.failed(
                RuleCode.REQUESTER_IS_NOT_THE_ASSIGNED_WORKER,
                f"Actor {requester.id} is not the Worker assigned to Task {task.id}",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("assigned_worker_id", [task.assigned_worker_id]),
                RuleDetail.of("requester_id", [requester.id]),
            )

        return self.passed(f"Actor {requester.id} is the Worker assigned to Task {task.id}")


class ReviewerAssignedRule(Rule):
    """A submitted Task must be routed to an eligible Reviewer (ADR-007 7.3).

    Blueprint 5.2 ``SUBMITTED -> IN_REVIEW`` requires an assigned Reviewer and
    describes automatic routing. Neither the field nor the routing model existed
    until ADR-007 7.3 ruled on them, which is why this condition sat in
    ``BLOCKED_CONDITIONS`` rather than in the backlog.

    Four things must hold, each with its own failure code so a refusal names
    what to fix:

    1. A Reviewer is recorded on the Task.
    2. That Reviewer is among the Actors the OS may route to — active, holding
       the ``REVIEWER`` role.
    3. Their declared capabilities contain the Task's capability.
    4. **They did not perform the work.**

    Point 4 is ADR-001 — *work is never completed by the agent that performs
    it* — made enforceable for the first time. It is checked against the
    assigned Worker **and** the author of every Revision, through the same
    ``work_authors`` the router uses, because a Task can change hands: an Actor
    who authored an earlier Revision worked on it whether or not they are still
    assigned.

    **Routing proposes; this rule enforces, and it does not trust the
    proposal.** It re-derives eligibility from the same facts rather than
    accepting that a Reviewer appears on the Task, so a Reviewer recorded by any
    other path is refused just as one the router chose wrongly would be.

    The Task model refuses to record the assigned Worker as the Reviewer and a
    database ``CHECK`` refuses to store it. This rule is the third guard and the
    only one that can see the Revision history, so it is the only one that can
    catch a previous author.

    **An empty candidate set is a refusal, not an error.** When no Reviewer is
    eligible the Task carries none, and this rule reports that with a reason and
    leaves a durable audit record — which is what a requester needs, and what an
    exception raised during routing would not give them.
    """

    rule_id = RuleId.REVIEWER_ASSIGNED
    condition = TransitionCondition.REVIEWER_ASSIGNED
    stage = RuleStage.ACTOR_AUTHORITY
    required_facts = frozenset(
        {RuleFact.TASK, RuleFact.CANDIDATE_REVIEWERS, RuleFact.TASK_REVISIONS}
    )

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether an eligible Reviewer is routed this Task."""
        task = context.require_task()
        candidates = context.require_candidate_reviewers()
        revisions = context.require_task_revisions()

        if task.reviewer_id is None:
            return self.failed(
                RuleCode.NO_REVIEWER_ROUTED,
                f"Task {task.id} records no Reviewer, so it cannot enter review",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("candidate_reviewer_ids", (actor.id for actor in candidates)),
            )

        identity = (
            RuleDetail.of("task_id", [task.id]),
            RuleDetail.of("reviewer_id", [task.reviewer_id]),
        )

        routed = next(
            (actor for actor in candidates if task.is_reviewed_by(actor.id)),
            None,
        )
        if routed is None:
            return self.failed(
                RuleCode.REVIEWER_NOT_ELIGIBLE,
                f"Task {task.id} names a Reviewer that is not an active Reviewer the OS "
                f"may route to",
                RuleDetail.of("candidate_reviewer_ids", (actor.id for actor in candidates)),
                *identity,
            )

        if not routed.can_review(task.capability):
            return self.failed(
                RuleCode.REVIEWER_CAPABILITY_MISMATCH,
                f"Reviewer {routed.id} does not declare the capability {task.capability} "
                f"required by Task {task.id}",
                RuleDetail.of("required_capability", [task.capability]),
                RuleDetail.of("reviewer_capabilities", sorted(routed.capabilities)),
                *identity,
            )

        authors = work_authors(task, revisions)
        if routed.id in authors:
            return self.failed(
                RuleCode.REVIEWER_PERFORMED_THE_WORK,
                f"Actor {routed.id} performed work on Task {task.id} and cannot review it",
                RuleDetail.of("work_author_ids", sorted(authors)),
                *identity,
            )

        return self.passed(f"Task {task.id} is routed to eligible Reviewer {routed.id}")
