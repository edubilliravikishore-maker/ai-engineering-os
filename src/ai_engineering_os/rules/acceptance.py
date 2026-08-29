"""Feature acceptance rules — evaluation stage 5 (ADR-004 4.10).

These three rules govern Feature ``IN_VALIDATION -> ACCEPTED``. Two of them are
independent, so their failures aggregate into one explicit missing list; the
third declares a prerequisite, so it is skipped rather than producing a
misleading verdict once its premise has collapsed.
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import TaskStatus
from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.identifiers import TaskId
from ai_engineering_os.domain.qa import QADefect
from ai_engineering_os.domain.task import Task
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult

__all__ = [
    "AllTasksAcceptedRule",
    "QAFinalPassRecordedRule",
    "QAInScopeZeroDefectsRule",
]


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
            for report in context.require_qa_reports()
            if report.feature_id == feature.id and report.is_final_pass
        )

        if not final_passes:
            return self.failed(
                RuleCode.MISSING_QA_FINAL_PASS,
                f"Feature {feature.id} records no QA Final Pass",
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

        return self.passed(f"Feature {feature.id} records a valid QA Final Pass")


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

    **Caller-supplied precondition (ADR-004 4.4, 4.15).** This rule evaluates
    the QA Reports it is given and takes no view on how many there are. Which
    QA result is **authoritative** for a Feature is deliberately **not decided
    here and is not this rule's concern**: selecting it is the responsibility of
    the Checkpoint 6 Kernel / context loader that assembles the ``RuleContext``.

    That boundary matters. QA Reports are immutable audit history, and repeat QA
    is normal — a report exists per Task Revision, and the Blueprint 5.1
    ``IN_VALIDATION -> IN_PROGRESS`` rework loop produces more of them. A rule
    that inspected how many reports it received, or that preferred one over
    another, would be inventing QA workflow semantics it does not own. So this
    rule invents none: no ordering, no recency, no "latest" marker, no session
    identity, and no additional context fact.

    The consequence is stated plainly rather than guarded against: if a caller
    supplies superseded reports, their unresolved defects are evaluated as
    supplied. Preventing that is the loader's job, not this rule's, and the
    authoritative-QA-result mechanism remains an open architectural question
    (ADR-004 *Questions Not Decided*, item 7).
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
        reports = tuple(
            report for report in context.require_qa_reports() if report.feature_id == feature.id
        )

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

        return self.passed(f"Feature {feature.id} carries no unresolved in-scope defect")


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
