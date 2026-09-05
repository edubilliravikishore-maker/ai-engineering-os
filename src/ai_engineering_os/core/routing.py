"""Reviewer routing (ADR-007 7.3).

The Blueprint 5.2 ``SUBMITTED -> IN_REVIEW`` edge describes automatic routing to
an assigned Reviewer. Until ADR-007 7.3 neither the field nor the model existed,
so the condition sat in ``BLOCKED_CONDITIONS`` rather than in a backlog.

**Selection is deterministic and it fails closed.** The OS never invents a
Reviewer, never falls back to the Builder, and never lets an unreviewed Task
advance because nobody was available.

This module decides *who*. Whether the choice was legitimate is re-checked by
``ReviewerAssignedRule`` against the same facts — routing proposes, the Rule
Engine enforces, and the enforcement does not trust the proposal.
"""

from collections.abc import Sequence

from ai_engineering_os.domain.actor import Actor
from ai_engineering_os.domain.task import Task, TaskRevision, work_authors

__all__ = ["eligible_reviewers", "select_reviewer"]


def eligible_reviewers(
    task: Task,
    candidates: Sequence[Actor],
    revisions: Sequence[TaskRevision],
) -> tuple[Actor, ...]:
    """Returns the Actors who may review ``task``, ordered by identifier.

    Eligibility is the four-part test of ADR-007 7.3: an active ``REVIEWER``
    holding the Task's capability who did not perform the work. "Who performed
    the work" is answered by ``domain.task.work_authors`` — the same function
    ``ReviewerAssignedRule`` uses, so the router and the rule cannot disagree.

    The order is the tie-break, applied here so the result is reproducible
    regardless of the order the candidates arrived in.
    """
    authors = work_authors(task, revisions)
    eligible = [
        candidate
        for candidate in candidates
        if candidate.can_review(task.capability) and candidate.id not in authors
    ]
    return tuple(sorted(eligible, key=lambda actor: actor.id))


def select_reviewer(
    task: Task,
    candidates: Sequence[Actor],
    revisions: Sequence[TaskRevision],
) -> Actor | None:
    """Returns the Reviewer to route ``task`` to, or ``None`` when there is none.

    ``None`` is a real answer meaning *no eligible Reviewer exists*, and the
    Kernel refuses the transition on it. It is deliberately not an exception:
    the refusal carries a rejection reason the requester can act on, and a
    durable audit record, which an exception thrown out of routing would not.
    """
    eligible = eligible_reviewers(task, candidates, revisions)
    return eligible[0] if eligible else None
