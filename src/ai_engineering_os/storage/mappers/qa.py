"""QA Report and QA Defect <-> row mapping.

Defects are child rows, ordered by ``position`` so the report's defect tuple
round-trips exactly.

``evidence_ids`` is stored as a JSONB list on the report, exactly as the domain
models it. It is deliberately **not** derived from ``evidence_records`` — the
domain records both directions, and deriving one would make the report's own
statement of which Evidence it cites dependent on insertion order elsewhere.
"""

from collections.abc import Sequence

from ai_engineering_os.domain.qa import QAReport
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.qa import QADefectRow, QAReportRow

__all__ = ["to_defect_rows", "to_domain_qa_report", "to_qa_report_row"]


def to_domain_qa_report(row: QAReportRow, defects: Sequence[QADefectRow]) -> QAReport:
    """Rebuilds the immutable QA Report recorded by ``row`` and its defect rows."""
    ordered = sorted(defects, key=lambda defect: defect.position)
    return reconstruct(
        QAReport,
        {
            "id": row.id,
            "feature_id": row.feature_id,
            "status": row.status,
            "task_revision_id": row.task_revision_id,
            "is_final_pass": row.is_final_pass,
            "tested_scope": row.tested_scope,
            "results": row.results,
            "defects": [
                {
                    "id": defect.id,
                    "title": defect.title,
                    "severity": defect.severity,
                    "priority": defect.priority,
                    "is_blocker": defect.is_blocker,
                    "status": defect.status,
                    "scope_task_id": defect.scope_task_id,
                    "scope_feature_id": defect.scope_feature_id,
                }
                for defect in ordered
            ],
            "evidence_ids": row.evidence_ids,
            "created_at": row.created_at,
        },
        entity_id=row.id,
    )


def to_qa_report_row(report: QAReport) -> QAReportRow:
    """Builds the append-only row recording ``report``."""
    return QAReportRow(
        id=report.id,
        feature_id=report.feature_id,
        status=report.status.value,
        task_revision_id=report.task_revision_id,
        is_final_pass=report.is_final_pass,
        tested_scope=list(report.tested_scope),
        results=[result.model_dump(mode="json") for result in report.results],
        evidence_ids=[str(evidence_id) for evidence_id in report.evidence_ids],
        created_at=report.created_at,
    )


def to_defect_rows(report: QAReport) -> list[QADefectRow]:
    """Builds the child rows recording ``report``'s defects, in order.

    Both scope columns are written exactly as recorded, including the both-null
    case: ADR-004 4.8 requires unresolved scope to stay representable.
    """
    return [
        QADefectRow(
            id=defect.id,
            qa_report_id=report.id,
            position=position,
            title=defect.title,
            severity=defect.severity,
            priority=defect.priority,
            is_blocker=defect.is_blocker,
            status=defect.status.value,
            scope_task_id=defect.scope_task_id,
            scope_feature_id=defect.scope_feature_id,
        )
        for position, defect in enumerate(report.defects)
    ]
