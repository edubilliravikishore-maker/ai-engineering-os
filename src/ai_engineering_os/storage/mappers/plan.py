"""Feature Plan <-> row mapping, including its plan-local task definitions.

``position`` preserves the order of the ``task_definitions`` tuple across a round
trip. It is a persistence mechanism and carries no domain meaning.
"""

from collections.abc import Sequence

from ai_engineering_os.domain.plan import FeaturePlan
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.plan import FeaturePlanRow, PlanTaskDefinitionRow

__all__ = ["apply_plan", "to_domain_plan", "to_plan_definition_rows", "to_plan_row"]


def to_domain_plan(
    row: FeaturePlanRow, definitions: Sequence[PlanTaskDefinitionRow]
) -> FeaturePlan:
    """Rebuilds the domain Feature Plan recorded by ``row`` and its definitions."""
    ordered = sorted(definitions, key=lambda definition: definition.position)
    return reconstruct(
        FeaturePlan,
        {
            "id": row.id,
            "feature_id": row.feature_id,
            "revision_number": row.revision_number,
            "created_by": row.created_by,
            "status": row.status,
            "required_capabilities": row.required_capabilities,
            "task_definitions": [
                {
                    "key": definition.key,
                    "title": definition.title,
                    "capability": definition.capability,
                    "depends_on": definition.depends_on,
                }
                for definition in ordered
            ],
            "created_at": row.created_at,
        },
        entity_id=row.id,
    )


def apply_plan(plan: FeaturePlan, row: FeaturePlanRow) -> None:
    """Writes the plan's own columns onto ``row``.

    Task definitions are child rows and are not written here: a plan revision is
    a new plan, so definitions are inserted with their plan rather than rewritten.
    """
    row.feature_id = plan.feature_id
    row.revision_number = plan.revision_number
    row.created_by = plan.created_by
    row.status = plan.status.value
    row.required_capabilities = [capability.value for capability in plan.required_capabilities]
    row.created_at = plan.created_at


def to_plan_row(plan: FeaturePlan) -> FeaturePlanRow:
    """Builds a new row for ``plan``."""
    row = FeaturePlanRow(id=plan.id, version=1)
    apply_plan(plan, row)
    return row


def to_plan_definition_rows(plan: FeaturePlan) -> list[PlanTaskDefinitionRow]:
    """Builds the child rows recording ``plan``'s task definitions, in order."""
    return [
        PlanTaskDefinitionRow(
            feature_plan_id=plan.id,
            key=definition.key,
            position=position,
            title=definition.title,
            capability=definition.capability.value,
            depends_on=list(definition.depends_on),
        )
        for position, definition in enumerate(plan.task_definitions)
    ]
