"""Explicit domain <-> row translation (ADR-005 5.3, 5.11).

Mapping is written by hand rather than inferred. The domain models are frozen
and fully revalidated on construction; SQLAlchemy needs mutable instances to
track changes. The two are structurally incompatible, and this package is the
seam between them.

Nothing here reads a persistence metadata column (ADR-005 5.9), and nothing here
returns a SQLAlchemy model to a caller outside ``storage`` (ADR-005 5.11).
"""

from ai_engineering_os.storage.mappers.actor import apply_actor, to_actor_row, to_domain_actor
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.mappers.decision import (
    to_acknowledgement_row,
    to_acknowledgement_rows,
    to_decision_row,
    to_domain_decision,
    to_domain_review_decision,
    to_review_decision_row,
)
from ai_engineering_os.storage.mappers.evidence import to_domain_evidence, to_evidence_row
from ai_engineering_os.storage.mappers.feature import (
    apply_feature,
    to_domain_feature,
    to_feature_row,
)
from ai_engineering_os.storage.mappers.plan import (
    apply_plan,
    to_domain_plan,
    to_plan_definition_rows,
    to_plan_row,
)
from ai_engineering_os.storage.mappers.qa import (
    to_defect_rows,
    to_domain_qa_report,
    to_qa_report_row,
)
from ai_engineering_os.storage.mappers.task import (
    apply_task,
    to_domain_revision,
    to_domain_revision_history,
    to_domain_task,
    to_revision_row,
    to_task_dependency_rows,
    to_task_row,
)
from ai_engineering_os.storage.mappers.work_package import (
    apply_work_package,
    to_domain_work_package,
    to_work_package_row,
)

__all__ = [
    "apply_actor",
    "apply_feature",
    "apply_plan",
    "apply_task",
    "apply_work_package",
    "reconstruct",
    "to_acknowledgement_row",
    "to_acknowledgement_rows",
    "to_actor_row",
    "to_decision_row",
    "to_defect_rows",
    "to_domain_actor",
    "to_domain_decision",
    "to_domain_evidence",
    "to_domain_feature",
    "to_domain_plan",
    "to_domain_qa_report",
    "to_domain_review_decision",
    "to_domain_revision",
    "to_domain_revision_history",
    "to_domain_task",
    "to_domain_work_package",
    "to_evidence_row",
    "to_feature_row",
    "to_plan_definition_rows",
    "to_plan_row",
    "to_qa_report_row",
    "to_review_decision_row",
    "to_revision_row",
    "to_task_dependency_rows",
    "to_task_row",
    "to_work_package_row",
]
