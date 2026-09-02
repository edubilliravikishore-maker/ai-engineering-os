"""Feature Plan repository (ADR-005 5.4).

A plan's task definitions are inserted with the plan and are never rewritten: a
revised plan is a new plan revision, not an edit of the recorded one.
"""

from sqlalchemy import select

from ai_engineering_os.domain.identifiers import FeatureId, FeaturePlanId
from ai_engineering_os.domain.plan import FeaturePlan
from ai_engineering_os.storage.mappers.plan import (
    apply_plan,
    to_domain_plan,
    to_plan_definition_rows,
    to_plan_row,
)
from ai_engineering_os.storage.models.plan import FeaturePlanRow, PlanTaskDefinitionRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["FeaturePlanRepository"]


class FeaturePlanRepository(BaseRepository[FeaturePlanRow]):
    """Reads and writes Feature Plans and their plan-local task definitions."""

    row_type = FeaturePlanRow
    entity_name = "FeaturePlan"

    async def add(self, plan: FeaturePlan) -> None:
        """Records a new Feature Plan and its task definitions."""
        self._stage(to_plan_row(plan))
        await self._flush()
        for definition in to_plan_definition_rows(plan):
            self._session.add(definition)
        await self._flush()

    async def get_by_id(self, plan_id: FeaturePlanId) -> FeaturePlan:
        """Returns the Feature Plan recorded under ``plan_id``, with its definitions."""
        row = await self._require_row(plan_id)
        return to_domain_plan(row, await self._definitions_of(plan_id))

    async def list_by_feature(self, feature_id: FeatureId) -> tuple[FeaturePlan, ...]:
        """Returns every Feature Plan recorded against ``feature_id``, oldest revision first."""
        rows = await self._rows_where(
            FeaturePlanRow.feature_id == feature_id,
            order_by=FeaturePlanRow.revision_number,
        )
        plans = []
        for row in rows:
            plans.append(to_domain_plan(row, await self._definitions_of(FeaturePlanId(row.id))))
        return tuple(plans)

    async def save(self, plan: FeaturePlan) -> None:
        """Updates the recorded plan's own columns under optimistic locking.

        Task definitions are planning history and are not rewritten here.
        """
        row = await self._require_row(plan.id)
        await self._save_row(row, lambda target: apply_plan(plan, target))

    async def _definitions_of(self, plan_id: FeaturePlanId) -> list[PlanTaskDefinitionRow]:
        """Returns the task definition rows belonging to ``plan_id``, in recorded order."""
        statement = (
            select(PlanTaskDefinitionRow)
            .where(PlanTaskDefinitionRow.feature_plan_id == plan_id)
            .order_by(PlanTaskDefinitionRow.position)
        )
        with self._translating():
            result = await self._session.execute(statement)
        return list(result.scalars().all())
