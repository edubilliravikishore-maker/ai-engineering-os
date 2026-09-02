"""Work Package <-> row mapping (ADR-003 3.5, ADR-005 5.8).

The mapper writes both content and status. Enforcing that submitted **content**
is immutable is the repository's job, because only the repository can compare
what is being written against what is already stored.
"""

from typing import Any

from ai_engineering_os.domain.work_package import WorkPackage
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.work_package import WorkPackageRow

__all__ = ["apply_work_package", "to_domain_work_package", "to_work_package_row"]


def to_domain_work_package(row: WorkPackageRow) -> WorkPackage:
    """Rebuilds the domain Work Package recorded by ``row``."""
    data: dict[str, Any] = {
        "id": row.id,
        "task_revision_id": row.task_revision_id,
        "summary": row.summary,
        "status": row.status,
        "claims": row.claims,
        "verification_guide": row.verification_guide,
        "worker_notes": row.worker_notes,
        "risks": row.risks,
        "submitted_at": row.submitted_at,
    }
    return reconstruct(WorkPackage, data, entity_id=row.id)


def apply_work_package(work_package: WorkPackage, row: WorkPackageRow) -> None:
    """Writes ``work_package`` onto ``row``."""
    row.task_revision_id = work_package.task_revision_id
    row.summary = work_package.summary
    row.status = work_package.status.value
    row.claims = [claim.model_dump(mode="json") for claim in work_package.claims]
    row.verification_guide = (
        work_package.verification_guide.model_dump(mode="json")
        if work_package.verification_guide is not None
        else None
    )
    row.worker_notes = list(work_package.worker_notes)
    row.risks = work_package.risks
    row.submitted_at = work_package.submitted_at


def to_work_package_row(work_package: WorkPackage) -> WorkPackageRow:
    """Builds a new row for ``work_package``."""
    row = WorkPackageRow(id=work_package.id, version=1)
    apply_work_package(work_package, row)
    return row
