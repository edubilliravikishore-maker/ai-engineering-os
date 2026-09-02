"""Review Decision repository — append-only (ADR-003 3.2, ADR-005 5.8).

**There is no update method.** A review outcome is a permanent record of what one
Reviewer concluded about one Task Revision.

Deliberately separate from :mod:`decision_repo`: merging the two would place
every routine code review into permanent architectural decision history, and
``REVIEWER`` holds authority at no ``DecisionScope`` (ADR-003 3.2).

**Reviewer assignment and routing are not implemented here.** No domain concept
exists — ``Task`` carries no reviewer — and ``REVIEWER_ASSIGNED`` remains a
``BLOCKED_CONDITION`` on the Checkpoint 6 critical path (ADR-004 4.11).
"""

from ai_engineering_os.domain.decision import ReviewDecision
from ai_engineering_os.domain.identifiers import ReviewDecisionId, TaskRevisionId
from ai_engineering_os.storage.errors import NotFoundError
from ai_engineering_os.storage.mappers.decision import (
    to_domain_review_decision,
    to_review_decision_row,
)
from ai_engineering_os.storage.models.decision import ReviewDecisionRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["ReviewDecisionRepository"]


class ReviewDecisionRepository(BaseRepository[ReviewDecisionRow]):
    """Appends and reads immutable Reviewer outcomes."""

    row_type = ReviewDecisionRow
    entity_name = "ReviewDecision"

    async def add(self, review: ReviewDecision) -> None:
        """Appends a Review Decision within the caller's transaction."""
        self._stage(to_review_decision_row(review))
        await self._flush()

    async def get_by_id(self, review_id: ReviewDecisionId) -> ReviewDecision:
        """Returns the Review Decision recorded under ``review_id``."""
        return to_domain_review_decision(await self._require_row(review_id))

    async def list_by_task_revision(
        self, task_revision_id: TaskRevisionId
    ) -> tuple[ReviewDecision, ...]:
        """Returns every Review Decision recorded against ``task_revision_id``.

        A tuple rather than one record: nothing in the architecture limits a
        Revision to a single review, and inventing that limit here would be
        inventing workflow semantics this layer does not own.
        """
        rows = await self._rows_where(
            ReviewDecisionRow.task_revision_id == task_revision_id,
            order_by=ReviewDecisionRow.created_at,
        )
        return tuple(to_domain_review_decision(row) for row in rows)

    async def get_by_task_revision(self, task_revision_id: TaskRevisionId) -> ReviewDecision:
        """Returns the single Review Decision recorded against ``task_revision_id``.

        Raises:
            NotFoundError: if that Revision carries no Review Decision.
        """
        reviews = await self.list_by_task_revision(task_revision_id)
        if not reviews:
            raise NotFoundError(
                f"Task Revision {task_revision_id} carries no Review Decision",
                entity=self.entity_name,
                entity_id=task_revision_id,
            )
        return reviews[0]
