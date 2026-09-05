"""The OS Kernel (Blueprint 2.2, 15 Checkpoint 6).

**Only the Kernel mutates state, records audit, and publishes events**
(ADR-004 4.7). The state machine answers whether a transition is defined and
who may request it; the Rule Engine answers whether the declared conditions
hold; neither may write anything. This layer composes the two and owns the
transaction.

Every operation follows the same shape: load, assemble the facts, hand the
whole thing to the :class:`~ai_engineering_os.core.runner.TransitionRunner`, and
let it decide whether the mutation is applied. **No operation here mutates
before validation**, and no operation writes its own audit record or event —
doing either in a second place is how the Validation-First invariant gets lost.

Three operations do something beyond a plain transition, and each is a
Checkpoint 6 obligation rather than a convenience:

``activate_plan``
    Instantiates the Plan's Tasks inside the transition (ADR-003 3.12), which is
    what discharges ``TASKS_INSTANTIATED`` (ADR-007 7.5).

``route_for_review``
    Selects the Reviewer and records the routing in one operation (ADR-007 7.3),
    refusing when no eligible Reviewer exists.

``return_for_rework``
    Advances the Feature's QA round (ADR-007 7.4). **This is the only operation
    that changes ``qa_round``**, and the fact that no other one does is what
    makes the round trustworthy.
"""

from ai_engineering_os.core.context_loader import load_rule_context
from ai_engineering_os.core.routing import select_reviewer
from ai_engineering_os.core.runner import (
    TransitionRequest,
    TransitionResult,
    TransitionRunner,
    initiator_id_for,
)
from ai_engineering_os.domain.actor import Actor
from ai_engineering_os.domain.enums import (
    ActorRole,
    FeatureStatus,
    Initiator,
    PlanStatus,
    SystemActor,
    TaskStatus,
)
from ai_engineering_os.domain.event import EventType
from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.identifiers import (
    ActorId,
    FeatureId,
    FeaturePlanId,
    TaskId,
    new_id,
)
from ai_engineering_os.domain.plan import FeaturePlan, TaskDefinition
from ai_engineering_os.domain.qa import QAReport
from ai_engineering_os.domain.task import Task
from ai_engineering_os.state.feature_sm import FEATURE_STATE_MACHINE
from ai_engineering_os.state.task_sm import TASK_STATE_MACHINE
from ai_engineering_os.storage.unit_of_work import UnitOfWork

__all__ = ["OSKernel"]


class OSKernel:
    """The single component that turns a requested transition into a durable fact."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._runner = TransitionRunner(uow)

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    async def transition_task(
        self,
        task_id: TaskId,
        to_state: TaskStatus,
        *,
        initiator: Initiator,
        initiator_id: ActorId | None = None,
        candidate_worker_id: ActorId | None = None,
    ) -> TransitionResult:
        """Runs one Task transition to a durable outcome.

        The generic path. Transitions needing more than a status change have
        their own operation below, so that the extra work happens inside the
        same validated transaction rather than beside it.
        """
        task = await self._uow.tasks.get_by_id(task_id)
        context = await load_rule_context(
            self._uow,
            task=task,
            requesting_actor=await self._actor(initiator_id),
            candidate_worker=await self._actor(candidate_worker_id),
        )

        async def apply() -> None:
            await self._uow.tasks.save(task.with_status(to_state))

        return await self._runner.run(
            TransitionRequest(
                machine=TASK_STATE_MACHINE,
                entity_type="Task",
                entity_id=task.id,
                from_state=task.status,
                to_state=to_state,
                initiator=initiator,
                initiator_id=initiator_id_for(initiator, initiator_id),
                context=context,
                apply=apply,
            )
        )

    async def assign_task(
        self,
        task_id: TaskId,
        worker_id: ActorId,
        *,
        coordinator_id: ActorId,
    ) -> TransitionResult:
        """Assigns a READY Task to a Worker (Blueprint 5.2 ``READY -> ASSIGNED``)."""
        task = await self._uow.tasks.get_by_id(task_id)
        worker = await self._uow.actors.get_by_id(worker_id)
        context = await load_rule_context(
            self._uow,
            task=task,
            requesting_actor=await self._actor(coordinator_id),
            candidate_worker=worker,
        )

        async def apply() -> None:
            await self._uow.tasks.save(task.assign(worker_id))

        return await self._runner.run(
            TransitionRequest(
                machine=TASK_STATE_MACHINE,
                entity_type="Task",
                entity_id=task.id,
                from_state=task.status,
                to_state=TaskStatus.ASSIGNED,
                initiator=ActorRole.COORDINATOR,
                initiator_id=coordinator_id,
                context=context,
                apply=apply,
                allowed_event_type=EventType.TASK_ASSIGNED,
                payload={"worker_id": str(worker_id)},
            )
        )

    async def route_for_review(self, task_id: TaskId) -> TransitionResult:
        """Routes a SUBMITTED Task to an eligible Reviewer (ADR-007 7.3).

        The OS is the initiator: routing is something the OS does, not something
        an Actor requests, which is why Blueprint 5.2 names ``OS`` on this edge.

        **Refuses rather than raising when no Reviewer is eligible.** The
        refusal carries the reason and leaves a durable audit record; an
        exception thrown out of routing would leave neither, and a Task stuck
        with no explanation is the failure mode this checkpoint exists to
        prevent.
        """
        task = await self._uow.tasks.get_by_id(task_id)
        revisions = (await self._uow.task_revisions.get_history(task.id)).revisions
        candidates = await self._uow.actors.list_active_by_role(ActorRole.REVIEWER)
        reviewer = select_reviewer(task, candidates, revisions)

        routed = task if reviewer is None else task.routed_to_reviewer(reviewer.id)
        context = await load_rule_context(self._uow, task=routed, candidate_reviewers=candidates)

        async def apply() -> None:
            await self._uow.tasks.save(routed)

        return await self._runner.run(
            TransitionRequest(
                machine=TASK_STATE_MACHINE,
                entity_type="Task",
                entity_id=task.id,
                from_state=task.status,
                to_state=TaskStatus.IN_REVIEW,
                initiator=SystemActor.OS,
                initiator_id=None,
                context=context,
                apply=apply,
                payload={"reviewer_id": str(reviewer.id) if reviewer else None},
            )
        )

    # ------------------------------------------------------------------
    # Feature lifecycle
    # ------------------------------------------------------------------

    async def transition_feature(
        self,
        feature_id: FeatureId,
        to_state: FeatureStatus,
        *,
        initiator: Initiator,
        initiator_id: ActorId | None = None,
    ) -> TransitionResult:
        """Runs one Feature transition to a durable outcome."""
        feature = await self._uow.features.get_by_id(feature_id)
        context = await load_rule_context(
            self._uow, feature=feature, requesting_actor=await self._actor(initiator_id)
        )

        async def apply() -> None:
            await self._uow.features.save(feature.with_status(to_state))

        event_type = (
            EventType.FEATURE_ACCEPTED
            if to_state is FeatureStatus.ACCEPTED
            else EventType.STATE_TRANSITION_ALLOWED
        )
        return await self._runner.run(
            TransitionRequest(
                machine=FEATURE_STATE_MACHINE,
                entity_type="Feature",
                entity_id=feature.id,
                from_state=feature.status,
                to_state=to_state,
                initiator=initiator,
                initiator_id=initiator_id_for(initiator, initiator_id),
                context=context,
                apply=apply,
                allowed_event_type=event_type,
            )
        )

    async def return_for_rework(
        self, feature_id: FeatureId, *, initiator: Initiator, initiator_id: ActorId
    ) -> TransitionResult:
        """Sends a Feature back for rework, opening a new QA round (ADR-007 7.4).

        **The only operation that advances ``qa_round``.** One round is one
        build-and-check cycle, and the boundary falls here — where the work
        actually restarts — so a cycle's Task-level QA and the Feature-level
        validation that follows it always share a number.

        The increment and the status change are one call on the Feature
        (``opening_next_qa_round``), so a Feature can never be returned for
        rework without its round advancing.
        """
        feature = await self._uow.features.get_by_id(feature_id)
        context = await load_rule_context(
            self._uow, feature=feature, requesting_actor=await self._actor(initiator_id)
        )

        async def apply() -> None:
            await self._uow.features.save(feature.opening_next_qa_round())

        return await self._runner.run(
            TransitionRequest(
                machine=FEATURE_STATE_MACHINE,
                entity_type="Feature",
                entity_id=feature.id,
                from_state=feature.status,
                to_state=FeatureStatus.IN_PROGRESS,
                initiator=initiator,
                initiator_id=initiator_id_for(initiator, initiator_id),
                context=context,
                payload={"opened_qa_round": feature.qa_round + 1},
                apply=apply,
            )
        )

    # ------------------------------------------------------------------
    # Plan activation and Task instantiation
    # ------------------------------------------------------------------

    async def activate_plan(
        self, plan_id: FeaturePlanId, *, coordinator_id: ActorId
    ) -> TransitionResult:
        """Activates a READY Plan and instantiates its Tasks in one transaction.

        ADR-003 3.12: plan activation **performs** the instantiation, which is
        why ``TASKS_INSTANTIATED`` never needed a rule (ADR-007 7.5). Evaluating
        it before this ran would be asking whether something exists moments
        before creating it.

        The Feature moves ``PLANNED -> IN_PROGRESS`` and the Plan moves
        ``READY -> ACTIVE`` alongside the Tasks, all inside the one validated
        transaction. Instantiation is **reconciling**: a definition that already
        has a Task does not get a second one, so a retried activation is safe.
        """
        plan = await self._uow.feature_plans.get_by_id(plan_id)
        feature = await self._uow.features.get_by_id(plan.feature_id)
        context = await load_rule_context(
            self._uow, feature=feature, requesting_actor=await self._actor(coordinator_id)
        )

        async def apply() -> None:
            await self._instantiate(plan, feature)
            await self._uow.feature_plans.save(plan.with_status(PlanStatus.ACTIVE))
            await self._uow.features.save(feature.with_status(FeatureStatus.IN_PROGRESS))

        return await self._runner.run(
            TransitionRequest(
                machine=FEATURE_STATE_MACHINE,
                entity_type="Feature",
                entity_id=feature.id,
                from_state=feature.status,
                to_state=FeatureStatus.IN_PROGRESS,
                initiator=ActorRole.COORDINATOR,
                initiator_id=coordinator_id,
                context=context,
                apply=apply,
                allowed_event_type=EventType.FEATURE_PLAN_ACTIVATED,
                payload={"feature_plan_id": str(plan.id)},
            )
        )

    async def _instantiate(self, plan: FeaturePlan, feature: Feature) -> None:
        """Creates a Task for every definition the Plan does not already have one for."""
        existing = {
            task.plan_definition_key
            for task in await self._uow.tasks.list_by_feature(feature.id)
            if task.feature_plan_id == plan.id
        }
        created: dict[str, TaskId] = {}
        for definition in plan.task_definitions:
            if definition.key in existing:
                continue
            created[definition.key] = new_id(TaskId)

        for definition in plan.task_definitions:
            task_id = created.get(definition.key)
            if task_id is None:
                continue
            await self._uow.tasks.add(
                Task(
                    id=task_id,
                    feature_id=feature.id,
                    feature_plan_id=plan.id,
                    plan_definition_key=definition.key,
                    title=definition.title,
                    capability=definition.capability,
                    dependencies=_resolved_dependencies(definition, created),
                )
            )

    # ------------------------------------------------------------------
    # QA
    # ------------------------------------------------------------------

    async def record_qa_report(self, report: QAReport) -> QAReport:
        """Records a QA Report, stamping it with the Feature's current round.

        **The round is stamped here, from the Feature's own field, at the moment
        of recording** (ADR-007 7.4). It is never supplied by the reporting
        Actor and never derived from a clock, so a report written during one
        round but submitted after rework began stays in the round it was written
        for. Whatever round the caller put on the report is overwritten.

        This is not a transition — a QA Report is an appended record, not a
        state change — so it takes no runner and commits nothing. The caller's
        transaction owns it.
        """
        feature = await self._uow.features.get_by_id(report.feature_id)
        stamped = report.model_copy(update={"qa_round": feature.qa_round})
        await self._uow.qa_reports.add(stamped)
        return stamped

    # ------------------------------------------------------------------

    async def _actor(self, actor_id: ActorId | None) -> Actor | None:
        """Loads an Actor, or returns ``None`` when no identifier was supplied."""
        if actor_id is None:
            return None
        return await self._uow.actors.get_by_id(actor_id)


def _resolved_dependencies(
    definition: TaskDefinition, created: dict[str, TaskId]
) -> tuple[TaskId, ...]:
    """Maps a definition's plan-local dependency keys onto instantiated Task ids.

    A key with no instantiated Task is skipped rather than raising: the Plan
    already validated that every dependency key resolves within it
    (``FeaturePlan`` rejects otherwise), so the only way to reach that case is a
    reconciling activation where the dependency's Task already existed, and it
    is recorded on that Task rather than invented again here.
    """
    return tuple(created[key] for key in definition.depends_on if key in created)
