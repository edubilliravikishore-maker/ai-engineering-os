"""QA Report repository — append-only audit history (ADR-004 4.15, ADR-005 5.8).

**There is no update method**, and there is deliberately no notion of a "latest"
or "current" report. ``list_by_feature`` returns what was recorded and **takes no
view on cardinality**: repeat QA is normal, since a report is scoped to a Task
Revision and the rework loop produces more of them.

**Selecting the authoritative QA result is not this repository's job and is not
implemented anywhere in Checkpoint 4.** That mechanism remains UNRESOLVED
(ADR-004 4.15, Blueprint 14, item 18) and must be designed before Checkpoint 6.
No recency ordering, sequence number, timestamp comparison, "latest" marker,
``current_report_id``, or QA session identity exists here or in the schema.
"""

from sqlalchemy import select

from ai_engineering_os.domain.identifiers import FeatureId, QAReportId
from ai_engineering_os.domain.qa import QAReport
from ai_engineering_os.storage.mappers.qa import (
    to_defect_rows,
    to_domain_qa_report,
    to_qa_report_row,
)
from ai_engineering_os.storage.models.qa import QADefectRow, QAReportRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["QAReportRepository"]


class QAReportRepository(BaseRepository[QAReportRow]):
    """Appends and reads immutable QA Reports and their defects."""

    row_type = QAReportRow
    entity_name = "QAReport"

    async def add(self, report: QAReport) -> None:
        """Appends a QA Report and its defect rows."""
        self._stage(to_qa_report_row(report))
        await self._flush()
        for defect in to_defect_rows(report):
            self._session.add(defect)
        await self._flush()

    async def get_by_id(self, report_id: QAReportId) -> QAReport:
        """Returns the QA Report recorded under ``report_id``, with its defects."""
        row = await self._require_row(report_id)
        return to_domain_qa_report(row, await self._defects_of(report_id))

    async def list_by_feature(self, feature_id: FeatureId) -> tuple[QAReport, ...]:
        """Returns every QA Report recorded against ``feature_id``.

        Ordered by the domain's own ``created_at`` for stable, reproducible
        output — **not** as a claim about which report is authoritative. That
        question is deliberately unanswered here.
        """
        rows = await self._rows_where(
            QAReportRow.feature_id == feature_id, order_by=QAReportRow.created_at
        )
        reports = []
        for row in rows:
            reports.append(to_domain_qa_report(row, await self._defects_of(QAReportId(row.id))))
        return tuple(reports)

    async def _defects_of(self, report_id: QAReportId) -> list[QADefectRow]:
        """Returns the defect rows belonging to ``report_id``, in recorded order."""
        statement = (
            select(QADefectRow)
            .where(QADefectRow.qa_report_id == report_id)
            .order_by(QADefectRow.position)
        )
        with self._translating():
            result = await self._session.execute(statement)
        return list(result.scalars().all())
