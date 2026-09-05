"""Shared fact selectors used by more than one rule.

Two selections are performed by rules rather than by the caller, and both live
here rather than being duplicated, so no two rules can disagree about which
record they are looking at.

**Selection belongs in the enforcement layer** (ADR-007 7.4). Checkpoint 3
deferred the QA-report choice to the context loader, correctly, because no
selector existed and preferring one report over another would have been
inventing QA workflow semantics. One now exists as a domain field requiring no
lookup, and leaving the filter to the caller would put enforcement outside the
component that enforces: every caller would have to get it right, and a caller
that did not would produce a silently wrong verdict rather than a refusal.

Neither selector performs I/O, reads a clock, or orders by a timestamp.
"""

from collections.abc import Sequence

from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.qa import QAReport
from ai_engineering_os.domain.task import Task, TaskRevision

__all__ = ["active_revision", "current_round_reports"]


def current_round_reports(feature: Feature, reports: Sequence[QAReport]) -> tuple[QAReport, ...]:
    """Returns the Feature's QA Reports belonging to its **current** round.

    One round is one build-and-check cycle (ADR-007 7.4). Reports from earlier
    rounds are permanent history stating what was true then; they are never
    re-evaluated as the Feature's current defect position, and they are never
    edited or discarded to achieve that.

    Nothing here reads a timestamp or a sequence number: ADR-005 5.9 and
    ADR-006 6.1 both stand.
    """
    return tuple(
        report
        for report in reports
        if report.feature_id == feature.id and report.qa_round == feature.qa_round
    )


def active_revision(task: Task, revisions: Sequence[TaskRevision]) -> TaskRevision | None:
    """Returns the Task's active Revision, or ``None`` when it has none.

    Active-ness is **derived**, never stored (ADR-003 3.1): the authoritative
    pointer is ``Task.active_revision_number`` and a Revision carries no marker
    of its own. A Task before its first submission has ``0`` and no active
    Revision, which is a real answer rather than a missing fact.
    """
    if task.active_revision_number < 1:
        return None
    for revision in revisions:
        if revision.task_id == task.id and revision.revision_number == task.active_revision_number:
            return revision
    return None
