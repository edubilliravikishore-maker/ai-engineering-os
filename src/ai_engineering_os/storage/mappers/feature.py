"""Feature <-> row mapping."""

from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.feature import FeatureRow

__all__ = ["apply_feature", "to_domain_feature", "to_feature_row"]


def to_domain_feature(row: FeatureRow) -> Feature:
    """Rebuilds the domain Feature recorded by ``row``."""
    return reconstruct(
        Feature,
        {
            "id": row.id,
            "slug": row.slug,
            "title": row.title,
            "goal": row.goal,
            "coordinator_id": row.coordinator_id,
            "status": row.status,
            "requirements": row.requirements,
            "in_scope": row.in_scope,
            "out_of_scope": row.out_of_scope,
            "acceptance_criteria": row.acceptance_criteria,
            "qa_round": row.qa_round,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        },
        entity_id=row.id,
    )


def apply_feature(feature: Feature, row: FeatureRow) -> None:
    """Writes ``feature`` onto ``row``."""
    row.slug = feature.slug
    row.title = feature.title
    row.goal = feature.goal
    row.coordinator_id = feature.coordinator_id
    row.status = feature.status.value
    row.requirements = list(feature.requirements)
    row.in_scope = list(feature.in_scope)
    row.out_of_scope = list(feature.out_of_scope)
    row.acceptance_criteria = list(feature.acceptance_criteria)
    row.qa_round = feature.qa_round
    row.created_at = feature.created_at
    row.updated_at = feature.updated_at


def to_feature_row(feature: Feature) -> FeatureRow:
    """Builds a new row for ``feature``."""
    row = FeatureRow(id=feature.id, version=1)
    apply_feature(feature, row)
    return row
