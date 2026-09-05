"""Feature acceptance rules — evaluation stage 5 (ADR-004 4.10; ADR-007 7.1, 7.4).

Four rules across the two Feature gates.

``ImplementationTasksAcceptedRule`` governs ``IN_PROGRESS -> IN_VALIDATION``:
may checking begin? The other three govern ``IN_VALIDATION -> ACCEPTED``: is
this Feature done? Two of those are independent, so their failures aggregate
into one explicit missing list; the third declares a prerequisite, so it is
skipped rather than producing a misleading verdict once its premise has
collapsed.

**The QA rules select the current round** (ADR-007 7.4). See
:mod:`ai_engineering_os.rules.selection` for why that selection is performed
here rather than by the caller.
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import CapabilityType, TaskStatus
from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.identifiers import TaskId
from ai_engineering_os.domain.qa import QADefect
from ai_engineering_os.domain.task import Task
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult
from ai_engineering_os.rules.selection import current_round_reports

__all__ = [
    "AllTasksAcceptedRule",
    "ImplementationTasksAcceptedRule",
    "QAFinalPassRecordedRule",
    "QAInScopeZeroDefectsRule",
]


class ImplementationTasksAcceptedRule(Rule):
    """Every implementation Task must be ACCEPTED before validation may begin.

    Blueprint 5.1 ``IN_PROGRESS -> IN_VALIDATION``, ruled by ADR-007 7.1.

    **An implementation Task is any Task whose capability is not QA.** That is a
    Builder ruling, not an inference. Blueprint 14 item 15 was right that
    *deriving* the definition inside an implementation would be inventing
    architecture; the same predicate stated deliberately, with its rationale and
    its cost recorded, is not. What was forbidden was the silence.

    **Why QA-capability Tasks are excluded.** A QA Task on a Feature exists to
    verify that Feature. Requiring it to be ``ACCEPTED`` before the Feature may
    enter ``IN_VALIDATION`` would make validation wait on work whose purpose is
    to perform validation, and the condition would be unsatisfiable for any
    Feature carrying one.

    **Nothing escapes acceptance.** ``AllTasksAcceptedRule`` covers *every* Task
    including QA at the next gate. The two rules differ by exactly the QA Tasks,
    which is why both exist: this one decides when checking may **begin**, that
    one decides when the Feature is **done**.

    **There is no exemption and no off-switch.** A research or spike Task
    attached to a Feature blocks it like any other, because a per-Task
    non-blocking flag would be defeated by the first mislabelled record. If
    non-blocking work proves genuinely necessary, ADR-007 7.1 records that the
    answer is a new ``CapabilityType`` ruled deliberately, not a flag.
    """

    rule_id = RuleId.IMPLEMENTATION_TASKS_ACCEPTED
    condition = TransitionCondition.ALL_IMPLEMENTATION_TASKS_ACCEPTED
    stage = RuleStage.ACCEPTANCE
    required_facts = frozenset({RuleFact.FEATURE, RuleFact.FEATURE_TASKS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether every non-QA Task of the Feature is ACCEPTED."""
        feature = context.require_feature()
        implementation = tuple(
            task
            for task in context.require_feature_tasks()
            if task.feature_id == feature.id and task.capability is not CapabilityType.QA
        )

        if not implementation:
            return self.failed(
                RuleCode.NO_IMPLEMENTATION_TASKS_RECORDED,
                f"Feature {feature.id} records no implementation Task, so there is nothing "
                f"built to validate",
                RuleDetail.of("feature_id", [feature.id]),
            )

        unaccepted = tuple(
            task for task in implementation if task.status is not TaskStatus.ACCEPTED
        )
        if unaccepted:
            return self.failed(
                RuleCode.IMPLEMENTATION_TASK_NOT_ACCEPTED,
                f"Feature {feature.id} has {len(unaccepted)} implementation Task(s) that are "
                f"not ACCEPTED",
                RuleDetail.of("unaccepted_task_ids", (task.id for task in unaccepted)),
                RuleDetail.of("unaccepted_task_statuses", (task.status for task in unaccepted)),
                RuleDetail.of("unaccepted_task_capabilities", (t.capability for t in unaccepted)),
                RuleDetail.of("feature_id", [feature.id]),
            )

        return self.passed(
            f"All {len(implementation)} implementation Tasks of Feature {feature.id} are ACCEPTED"
        )


class AllTasksAcceptedRule(Rule):
    """Every Task belonging to the Feature must be ``ACCEPTED``.

    Deliberately independent of ``qa_final_pass_recorded``: unfinished Tasks and
    a missing QA Final Pass are separate problems with separate remedies, so
    both must be reported in one rejection rather than discovered one reject
    cycle at a time.
    """

    rule_id = RuleId.ALL_TASKS_ACCEPTED
    condition = TransitionCondition.ALL_TASKS_ACCEPTED
    stage = RuleStage.ACCEPTANCE
    required_facts = frozenset({RuleFact.FEATURE, RuleFact.FEATURE_TASKS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether every Task recorded against the Feature is ACCEPTED."""
        feature = context.require_feature()
        tasks = tuple(
            task for task in context.require_feature_tasks() if task.feature_id == feature.id
        )

        if not tasks:
            return self.failed(
                RuleCode.NO_TASKS_RECORDED,
                f"Feature {feature.id} records no Task, so there is no delivered work to accept",
                RuleDetail.of("feature_id", [feature.id]),
            )

        unaccepted = tuple(task for task in tasks if task.status is not TaskStatus.ACCEPTED)
        if unaccepted:
            return self.failed(
                RuleCode.TASK_NOT_ACCEPTED,
                f"Feature {feature.id} has {len(unaccepted)} Task(s) that are not ACCEPTED",
                RuleDetail.of("unaccepted_task_ids", (task.id for task in unaccepted)),
                RuleDetail.of("unaccepted_task_statuses", (task.status for task in unaccepted)),
                RuleDetail.of("feature_id", [feature.id]),
            )

        return self.passed(f"All {len(tasks)} Tasks of Feature {feature.id} are ACCEPTED")


class QAFinalPassRecordedRule(Rule):
    """A valid QA Final Pass must be recorded for the Feature.

    Validity uses the QA Report's own recorded semantics
    (``QAReport.is_valid_final_pass``): a Final Pass that passed with zero
    unresolved defects. A report that merely claims to be a final pass is not
    accepted as one.

    **Only the current QA round counts** (ADR-007 7.4). A Final Pass recorded
    before the Feature was sent back for rework certified work that has since
    changed, so it cannot certify the Feature now. It stays on record as what
    was true then.
    """

    rule_id = RuleId.QA_FINAL_PASS_RECORDED
    condition = TransitionCondition.QA_FINAL_PASS_RECORDED
    stage = RuleStage.ACCEPTANCE
    required_facts = frozenset({RuleFact.FEATURE, RuleFact.QA_REPORTS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether a valid QA Final Pass exists for the Feature."""
        feature = context.require_feature()
        final_passes = tuple(
            report
            for report in current_round_reports(feature, context.require_qa_reports())
            if report.is_final_pass
        )

        if not final_passes:
            return self.failed(
                RuleCode.MISSING_QA_FINAL_PASS,
                f"Feature {feature.id} records no QA Final Pass in QA round {feature.qa_round}",
                RuleDetail.of("feature_id", [feature.id]),
            )

        valid = tuple(report for report in final_passes if report.is_valid_final_pass)
        if not valid:
            return self.failed(
                RuleCode.INVALID_QA_FINAL_PASS,
                f"Feature {feature.id} records {len(final_passes)} QA Final Pass report(s), "
                f"none of which is a valid pass",
                RuleDetail.of("qa_report_ids", (report.id for report in final_passes)),
                RuleDetail.of("qa_report_statuses", (report.status for report in final_passes)),
                RuleDetail.of(
                    "unresolved_defect_counts",
                    (len(report.unresolved_defects) for report in final_passes),
                ),
                RuleDetail.of("feature_id", [feature.id]),
            )

        return self.passed(
            f"Feature {feature.id} records a valid QA Final Pass in QA round {feature.qa_round}"
        )


class QAInScopeZeroDefectsRule(Rule):
    """No unresolved defect may resolve to the Feature under acceptance.

    Scope is **derived from a validated structural association**, never from a
    QA-supplied boolean (ADR-003 3.11). The model carries no ``in_scope`` field
    to read, because a self-assessment is not independent validation.

    **Resolution.**

    ``Defect -> Task -> Feature``
        The defect names the Task it was found against; that Task's Feature is
        the Feature the defect belongs to.

    ``Defect -> Feature``
        No Task represents the affected capability, so the defect names the
        Feature directly.

    **A defect resolving to a different Feature is out of scope and does not
    block this Feature** (ADR-003 3.11 as amended 2026-08-29, ADR-004 4.14).
    It is permanently recorded: work outside the recorded scope is never
    silently treated as a missing requirement, and never silently discarded
    either.

    Scope is **unresolved** only when the OS genuinely cannot resolve the
    association — the defect carries none at all, or its Task association
    resolves to no supplied Task. Only genuinely unresolved scope blocks.

    Only **unresolved** (``OPEN``) defects are scope-resolved: a defect QA has
    already resolved does not block acceptance regardless of its association.

    **Which QA Reports count (ADR-007 7.4).** Only those of the Feature's
    **current QA round**. One round is one build-and-check cycle: the build, its
    Task-level QA, and the Feature-level validation that follows it.

    This rule performed no selection at all until ADR-007 7.4 was ruled, and said
    so in this docstring. The Checkpoint 3 reasoning was right at the time — QA
    Reports are immutable history, repeat QA is normal, the ``IN_VALIDATION ->
    IN_PROGRESS`` rework loop produces more of them, and preferring one report
    over another with no architectural selector would have been inventing QA
    workflow semantics this rule does not own.

    **A selector now exists, and the filter belongs here rather than in the
    caller.** ``qa_round`` is a domain field requiring no lookup, no ordering, no
    recency comparison and no timestamp. Leaving the filter to the context loader
    would put enforcement outside the enforcement layer: every caller would have
    to get it right, and one that did not would produce a silently wrong verdict
    instead of a refusal.

    ``RuleFact.QA_REPORTS`` still means *every* report recorded against the
    Feature. This rule narrows them, and it narrows them the same way
    ``QAFinalPassRecordedRule`` does, through the one shared selector.

    The consequence the old note recorded — that superseded reports were
    evaluated as supplied — no longer holds. An ``OPEN`` defect from round 1
    remains ``OPEN`` in that record forever, and stops blocking the Feature once
    round 2 begins.
    """

    rule_id = RuleId.QA_IN_SCOPE_ZERO_DEFECTS
    condition = TransitionCondition.ZERO_UNRESOLVED_IN_SCOPE_DEFECTS
    stage = RuleStage.ACCEPTANCE
    required_facts = frozenset(
        {RuleFact.FEATURE, RuleFact.QA_REPORTS, RuleFact.FEATURE_TASKS, RuleFact.REFERENCED_TASKS}
    )
    requires = frozenset({RuleId.QA_FINAL_PASS_RECORDED})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether any unresolved defect resolves to this Feature."""
        feature = context.require_feature()
        reports = current_round_reports(feature, context.require_qa_reports())

        known_tasks: dict[TaskId, Task] = {
            task.id: task
            for task in (*context.require_feature_tasks(), *context.require_referenced_tasks())
        }

        blocking: list[QADefect] = []
        unresolved_scope: list[QADefect] = []
        for report in reports:
            for defect in report.defects:
                if not defect.is_unresolved:
                    continue
                if _is_scope_unresolved(defect, known_tasks):
                    unresolved_scope.append(defect)
                elif _resolves_to_feature(defect, feature, known_tasks):
                    blocking.append(defect)

        details = (
            RuleDetail.of("scope_unresolved_defect_ids", (d.id for d in unresolved_scope)),
            RuleDetail.of("scope_unresolved_defect_titles", (d.title for d in unresolved_scope)),
            RuleDetail.of("in_scope_defect_ids", (d.id for d in blocking)),
            RuleDetail.of("in_scope_defect_titles", (d.title for d in blocking)),
            RuleDetail.of("qa_round", [feature.qa_round]),
            RuleDetail.of("feature_id", [feature.id]),
        )

        if unresolved_scope:
            return self.failed(
                RuleCode.DEFECT_SCOPE_UNRESOLVED,
                f"Feature {feature.id} carries {len(unresolved_scope)} unresolved defect(s) whose "
                f"scope association does not resolve, so acceptance impact cannot be determined",
                *details,
            )

        if blocking:
            return self.failed(
                RuleCode.UNRESOLVED_IN_SCOPE_DEFECT,
                f"Feature {feature.id} carries {len(blocking)} unresolved in-scope defect(s)",
                *details,
            )

        return self.passed(
            f"Feature {feature.id} carries no unresolved in-scope defect in QA round "
            f"{feature.qa_round}"
        )


def _is_scope_unresolved(defect: QADefect, known_tasks: dict[TaskId, Task]) -> bool:
    """Returns whether the OS genuinely cannot resolve a defect's scope association.

    A Task association that resolves to no supplied Task is unresolved: the
    ``feature_tasks`` and ``referenced_tasks`` facts let the OS check that
    reference, so failing to resolve it is a real finding.

    A **Feature** association is unresolved only when it is absent. Checkpoint 3
    deliberately cannot tell an existing different Feature from a nonexistent
    Feature identifier, because the approved seven-fact ``RuleContext`` supplies
    only the Feature under acceptance and no ``known_feature_ids`` fact was added
    (ADR-004 4.16). Treating every non-matching identifier as dangling would
    contradict the approved out-of-scope interpretation; inventing a lookup would
    add a context fact Checkpoint 3 is not permitted to add.
    """
    if defect.scope_task_id is not None:
        return defect.scope_task_id not in known_tasks
    return defect.scope_feature_id is None


def _resolves_to_feature(
    defect: QADefect, feature: Feature, known_tasks: dict[TaskId, Task]
) -> bool:
    """Returns whether a scope-resolvable defect belongs to ``feature``."""
    if defect.scope_task_id is not None:
        return known_tasks[defect.scope_task_id].feature_id == feature.id
    return defect.scope_feature_id == feature.id
