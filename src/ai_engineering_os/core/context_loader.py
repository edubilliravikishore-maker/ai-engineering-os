"""The Rule Engine's context loader (ADR-004 4.4, 4.7; Blueprint 15 Checkpoint 6).

**This is the component Checkpoint 3 deliberately did not build.** A rule may
not reach a session, a repository, a clock or a random source, because a rule
that can fetch its own facts can fetch different facts on two identical calls.
So somebody has to read the facts and hand them over, and that somebody is here,
above both ``rules`` and ``storage``.

The loader **reads and assembles. It decides nothing.** It applies no filter a
rule would otherwise apply, and in particular it does **not** select which QA
Report is authoritative: it supplies every report recorded against the Feature
and the rules narrow them to the current round themselves (ADR-007 7.4). A
loader that pre-filtered would move enforcement out of the enforcement layer,
and a caller that filtered differently would get a silently different verdict
instead of a refusal.

Facts are loaded generously rather than per-edge. The engine selects the rules
for the requested conditions and verifies their facts are present, so supplying
more than one edge needs costs a few queries and removes a whole class of
``RuleContextIncompleteError`` that would otherwise depend on the caller knowing
which rules an edge happens to declare.
"""

from ai_engineering_os.domain.actor import Actor
from ai_engineering_os.domain.decision import ReviewDecision
from ai_engineering_os.domain.enums import ActorRole
from ai_engineering_os.domain.evidence import EvidenceRecord
from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.identifiers import TaskId
from ai_engineering_os.domain.plan import FeaturePlan
from ai_engineering_os.domain.qa import QAReport
from ai_engineering_os.domain.task import Task, TaskRevision
from ai_engineering_os.domain.work_package import WorkPackage
from ai_engineering_os.rules.context import RuleContext
from ai_engineering_os.storage.errors import NotFoundError
from ai_engineering_os.storage.unit_of_work import UnitOfWork

__all__ = ["load_rule_context"]


async def load_rule_context(
    uow: UnitOfWork,
    *,
    feature: Feature | None = None,
    task: Task | None = None,
    requesting_actor: Actor | None = None,
    candidate_worker: Actor | None = None,
    candidate_reviewers: tuple[Actor, ...] | None = None,
) -> RuleContext:
    """Assembles a :class:`RuleContext` for a transition on ``feature`` or ``task``.

    Either entity may be supplied; a Task's Feature is loaded when only the Task
    is given, because every Feature-scoped fact resolves through it.

    Args:
        uow: The open Unit of Work whose session every read goes through. The
            loader never opens one — the Kernel owns the transaction (ADR-005 5.5).
        feature: The Feature under evaluation, if the transition is a Feature's.
        task: The Task under evaluation, if the transition is a Task's.
        requesting_actor: The Actor who requested the transition.
        candidate_worker: The Actor proposed for an assignment.
        candidate_reviewers: The Actors the OS may route a submitted Task to.
            Loaded when not supplied, so a caller that does not care about
            review still gets a context every rule can be evaluated against.

    Returns:
        A frozen context carrying every fact resolvable from what was supplied.
    """
    resolved_feature = feature
    if resolved_feature is None and task is not None:
        resolved_feature = await uow.features.get_by_id(task.feature_id)

    revisions: tuple[TaskRevision, ...] = ()
    work_packages: tuple[WorkPackage, ...] = ()
    review_decisions: tuple[ReviewDecision, ...] = ()
    if task is not None:
        revisions = (await uow.task_revisions.get_history(task.id)).revisions
        work_packages = await _work_packages_of(uow, revisions)
        review_decisions = await _review_decisions_of(uow, revisions)

    feature_tasks: tuple[Task, ...] = ()
    feature_plans: tuple[FeaturePlan, ...] = ()
    qa_reports: tuple[QAReport, ...] = ()
    if resolved_feature is not None:
        feature_tasks = await uow.tasks.list_by_feature(resolved_feature.id)
        feature_plans = await uow.feature_plans.list_by_feature(resolved_feature.id)
        qa_reports = await uow.qa_reports.list_by_feature(resolved_feature.id)

    return RuleContext(
        candidate_worker=candidate_worker,
        candidate_reviewers=(
            candidate_reviewers
            if candidate_reviewers is not None
            else await uow.actors.list_active_by_role(ActorRole.REVIEWER)
        ),
        requesting_actor=requesting_actor,
        task=task,
        task_revisions=revisions,
        feature=resolved_feature,
        feature_tasks=feature_tasks,
        feature_plans=feature_plans,
        referenced_tasks=await _referenced_tasks(uow, task, feature_tasks, qa_reports),
        work_packages=work_packages,
        review_decisions=review_decisions,
        evidence=await _evidence_closure(uow, work_packages, qa_reports),
        qa_reports=qa_reports,
    )


async def _work_packages_of(
    uow: UnitOfWork, revisions: tuple[TaskRevision, ...]
) -> tuple[WorkPackage, ...]:
    """Returns the Work Packages recorded against ``revisions``.

    A Revision names its Work Package, so this resolves references rather than
    searching. A Revision that names none simply contributes nothing: an absent
    Work Package is a real finding for ``WorkPackagePresentRule`` to report, not
    a missing fact.
    """
    packages = []
    for revision in revisions:
        if revision.work_package_id is not None:
            packages.append(await uow.work_packages.get_by_id(revision.work_package_id))
    return tuple(packages)


async def _review_decisions_of(
    uow: UnitOfWork, revisions: tuple[TaskRevision, ...]
) -> tuple[ReviewDecision, ...]:
    """Returns every Review Decision recorded against ``revisions``.

    Queried per Revision rather than read from ``TaskRevision.review_decision_id``:
    nothing in the architecture limits a Revision to one review, and the
    repository says so explicitly. Reading only the named one would quietly
    impose a limit this layer does not own.
    """
    decisions: list[ReviewDecision] = []
    for revision in revisions:
        decisions.extend(await uow.review_decisions.list_by_task_revision(revision.id))
    return tuple(decisions)


async def _referenced_tasks(
    uow: UnitOfWork,
    task: Task | None,
    feature_tasks: tuple[Task, ...],
    qa_reports: tuple[QAReport, ...],
) -> tuple[Task, ...]:
    """Returns the Tasks named by identifiers held elsewhere.

    Two sources, both of which a rule must resolve without performing a lookup
    of its own: a Task's declared dependencies, and the Tasks QA defects
    associate with. Tasks already supplied as ``feature_tasks`` are excluded so
    the same Task is not handed over twice.

    **An identifier that resolves to nothing is left out**, deliberately. A
    defect naming a Task the OS cannot find is exactly the "scope unresolved"
    finding ``QAInScopeZeroDefectsRule`` exists to report, and quietly dropping
    the reference or raising here would take that judgement away from the rule.
    """
    known = {existing.id for existing in feature_tasks}
    wanted: set[TaskId] = set()
    if task is not None:
        wanted.update(task.dependencies)
    for report in qa_reports:
        wanted.update(
            defect.scope_task_id for defect in report.defects if defect.scope_task_id is not None
        )

    resolved: list[Task] = []
    for task_id in sorted(wanted - known):
        try:
            resolved.append(await uow.tasks.get_by_id(task_id))
        except NotFoundError:
            continue
    return tuple(resolved)


async def _evidence_closure(
    uow: UnitOfWork,
    work_packages: tuple[WorkPackage, ...],
    qa_reports: tuple[QAReport, ...],
) -> tuple[EvidenceRecord, ...]:
    """Returns the Evidence attached to the supplied Work Packages and QA Reports.

    This is the Feature's evidence closure of ADR-007 7.2 in its **unfiltered**
    form. Evidence from a superseded QA round is included here and excluded by
    ``FeatureEvidenceRequiredRule``, which knows the Feature's current round.
    Filtering it out at load time would hide from the rule the very facts it is
    responsible for judging.
    """
    records: list[EvidenceRecord] = []
    for package in work_packages:
        records.extend(await uow.evidence.list_by_work_package(package.id))
    for report in qa_reports:
        records.extend(await uow.evidence.list_by_qa_report(report.id))
    return tuple(records)
