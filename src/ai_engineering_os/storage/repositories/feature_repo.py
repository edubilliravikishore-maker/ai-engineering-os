"""Feature repository (ADR-005 5.4)."""

from sqlalchemy import select

from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.identifiers import FeatureId
from ai_engineering_os.storage.errors import NotFoundError
from ai_engineering_os.storage.mappers.feature import (
    apply_feature,
    to_domain_feature,
    to_feature_row,
)
from ai_engineering_os.storage.models.feature import FeatureRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["FeatureRepository"]


class FeatureRepository(BaseRepository[FeatureRow]):
    """Reads and writes Features."""

    row_type = FeatureRow
    entity_name = "Feature"

    async def add(self, feature: Feature) -> None:
        """Records a new Feature within the caller's transaction."""
        self._stage(to_feature_row(feature))
        await self._flush()

    async def get_by_id(self, feature_id: FeatureId) -> Feature:
        """Returns the Feature recorded under ``feature_id``."""
        return to_domain_feature(await self._require_row(feature_id))

    async def get_by_slug(self, slug: str) -> Feature:
        """Returns the Feature recorded under ``slug``.

        Raises:
            NotFoundError: if no Feature carries that slug.
        """
        statement = select(FeatureRow).where(FeatureRow.slug == slug)
        with self._translating():
            result = await self._session.execute(statement)
        row = result.scalars().one_or_none()
        if row is None:
            raise NotFoundError(
                f"No Feature is recorded under the slug {slug!r}",
                entity=self.entity_name,
                entity_id=slug,
            )
        return to_domain_feature(self._track(row))

    async def save(self, feature: Feature) -> None:
        """Updates the recorded Feature under optimistic locking."""
        row = await self._require_row(feature.id)
        await self._save_row(row, lambda target: apply_feature(feature, target))
