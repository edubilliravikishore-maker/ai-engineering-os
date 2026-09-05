"""Review and QA verification rules — evaluation stage 5 (ADR-004 4.3, 4.10).

Three rules governing the two gates that carry a Task from submitted work to
accepted work: ``IN_REVIEW -> IN_QA`` and ``IN_QA -> ACCEPTED``
(Blueprint 5.2).

All three resolve their record through the Task's **active Revision**. Review
and QA are per-Revision by design: a Task that came back for rework and was
resubmitted must be judged on the Revision under evaluation, never on the one
that was rejected. Active-ness is derived from ``Task.active_revision_number``
(ADR-003 3.1), so nothing here reads a marker or a timestamp.

``REVIEW_NOTES_PRESENT``, ``REVIEW_FEEDBACK_PRESENT`` and ``DEFECTS_DOCUMENTED``
have no rules and never will: the domain models make each of them
unconstructible otherwise (ADR-004 4.11).
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import EvidenceType, QAStatus
from ai_engineering_os.domain.qa import QAReport
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult
from ai_engineering_os.rules.selection import active_revision

__all__ = [
    "QAReportPassedRule",
    "ReviewDecisionApprovedRule",
    "TestExecutionEvidencePresentRule",
]


def _active_qa_report(context: RuleContext) -> QAReport | None:
    """Returns the QA Report recorded against the Task's active Revision."""
    task = context.require_task()
    revision = active_revision(task, context.require_task_revisions())
    if revision is None:
        return None
    for report in context.require_qa_reports():
        if report.task_revision_id == revision.id:
            return report
    return None


class ReviewDecisionApprovedRule(Rule):
    """The active Revision must carry an approving Review Decision.

    Blueprint 5.2 ``IN_REVIEW -> IN_QA``. A Task reaches QA because a Reviewer
    approved it, never because its status was moved. The decision is read from
    the Reviewer's own recorded outcome; nothing is inferred from the Task
    reaching this point.
    """

    rule_id = RuleId.REVIEW_DECISION_APPROVED
    condition = TransitionCondition.REVIEW_DECISION_APPROVED
    stage = RuleStage.ACCEPTANCE
    required_facts = frozenset({RuleFact.TASK, RuleFact.TASK_REVISIONS, RuleFact.REVIEW_DECISIONS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the active Revision was approved by its Reviewer."""
        task = context.require_task()
        revision = active_revision(task, context.require_task_revisions())

        if revision is None:
            return self.failed(
                RuleCode.NO_ACTIVE_REVISION,
                f"Task {task.id} has no active Revision, so nothing has been reviewed",
                RuleDetail.of("task_id", [task.id]),
            )

        decisions = tuple(
            decision
            for decision in context.require_review_decisions()
            if decision.task_revision_id == revision.id
        )

        if not decisions:
            return self.failed(
                RuleCode.NO_REVIEW_DECISION_RECORDED,
                f"Task Revision {revision.id} carries no Review Decision",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("task_revision_id", [revision.id]),
            )

        if not any(decision.is_approved for decision in decisions):
            return self.failed(
                RuleCode.REVIEW_CHANGES_REQUESTED,
                f"Task Revision {revision.id} was not approved by its Reviewer",
                RuleDetail.of("review_decision_ids", (d.id for d in decisions)),
                RuleDetail.of("review_outcomes", (d.outcome for d in decisions)),
                RuleDetail.of("task_id", [task.id]),
            )

        return self.passed(f"Task Revision {revision.id} carries an approving Review Decision")


class QAReportPassedRule(Rule):
    """The active Revision must carry a PASSED QA Report.

    Blueprint 5.2 ``IN_QA -> ACCEPTED``. ``BLOCKED`` and ``FAILED`` are both
    refusals, reported with the same code and the status in the details: what
    the requester must do — get QA to a pass — is identical either way.
    """

    rule_id = RuleId.QA_REPORT_PASSED
    condition = TransitionCondition.QA_REPORT_PASSED
    stage = RuleStage.ACCEPTANCE
    required_facts = frozenset({RuleFact.TASK, RuleFact.TASK_REVISIONS, RuleFact.QA_REPORTS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the active Revision's QA Report passed."""
        task = context.require_task()
        report = _active_qa_report(context)

        if report is None:
            return self.failed(
                RuleCode.NO_QA_REPORT_FOR_REVISION,
                f"Task {task.id} has no QA Report recorded against its active Revision",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("active_revision_number", [task.active_revision_number]),
            )

        if report.status is not QAStatus.PASSED:
            return self.failed(
                RuleCode.QA_REPORT_DID_NOT_PASS,
                f"QA Report {report.id} for Task {task.id} is {report.status}",
                RuleDetail.of("qa_report_id", [report.id]),
                RuleDetail.of("qa_status", [report.status]),
                RuleDetail.of("task_id", [task.id]),
            )

        return self.passed(f"Task {task.id} carries a PASSED QA Report {report.id}")


class TestExecutionEvidencePresentRule(Rule):
    """The QA Report must show tests were actually executed.

    Blueprint 5.2 ``IN_QA -> ACCEPTED``. Two things are required and both are
    checked: the report records test results, and ``TEST_OUTPUT`` Evidence is
    attached to it. A report claiming a pass with neither is an assertion, not a
    verification.

    Declares ``QA_REPORT_PASSED`` as a prerequisite. Once there is no report, or
    the report did not pass, asking whether its tests ran produces a verdict
    about a document nobody is relying on.
    """

    rule_id = RuleId.TEST_EXECUTION_EVIDENCE_PRESENT
    condition = TransitionCondition.TEST_EXECUTION_EVIDENCE_PRESENT
    stage = RuleStage.ACCEPTANCE
    required_facts = frozenset(
        {RuleFact.TASK, RuleFact.TASK_REVISIONS, RuleFact.QA_REPORTS, RuleFact.EVIDENCE}
    )
    requires = frozenset({RuleId.QA_REPORT_PASSED})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the QA Report evidences an actual test execution."""
        task = context.require_task()
        report = _active_qa_report(context)

        if report is None:
            return self.failed(
                RuleCode.NO_QA_REPORT_FOR_REVISION,
                f"Task {task.id} has no QA Report recorded against its active Revision",
                RuleDetail.of("task_id", [task.id]),
            )

        if not report.results:
            return self.failed(
                RuleCode.NO_TEST_RESULTS_RECORDED,
                f"QA Report {report.id} records no executed test",
                RuleDetail.of("qa_report_id", [report.id]),
                RuleDetail.of("task_id", [task.id]),
            )

        attached = tuple(
            record
            for record in context.require_evidence()
            if record.qa_report_id == report.id and record.evidence_type is EvidenceType.TEST_OUTPUT
        )
        if not attached:
            return self.failed(
                RuleCode.NO_TEST_EXECUTION_EVIDENCE,
                f"QA Report {report.id} records {len(report.results)} test result(s) but "
                f"attaches no {EvidenceType.TEST_OUTPUT} Evidence",
                RuleDetail.of("qa_report_id", [report.id]),
                RuleDetail.of("task_id", [task.id]),
            )

        return self.passed(
            f"QA Report {report.id} records {len(report.results)} test result(s) with "
            f"{len(attached)} attached test output(s)"
        )
