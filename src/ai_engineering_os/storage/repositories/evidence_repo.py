"""Evidence repository — append-only (ADR-005 5.8).

**There is no update method.** Evidence is durable, retrievable, and
integrity-verifiable; a record that could be rewritten would prove nothing.
"""

from ai_engineering_os.domain.evidence import EvidenceRecord
from ai_engineering_os.domain.identifiers import EvidenceId, QAReportId, WorkPackageId
from ai_engineering_os.storage.mappers.evidence import to_domain_evidence, to_evidence_row
from ai_engineering_os.storage.models.evidence import EvidenceRecordRow
from ai_engineering_os.storage.repositories.base import BaseRepository

__all__ = ["EvidenceRepository"]


class EvidenceRepository(BaseRepository[EvidenceRecordRow]):
    """Appends and reads immutable Evidence records."""

    row_type = EvidenceRecordRow
    entity_name = "EvidenceRecord"

    async def add(self, evidence: EvidenceRecord) -> None:
        """Appends an Evidence record within the caller's transaction."""
        self._stage(to_evidence_row(evidence))
        await self._flush()

    async def get_by_id(self, evidence_id: EvidenceId) -> EvidenceRecord:
        """Returns the Evidence record recorded under ``evidence_id``."""
        return to_domain_evidence(await self._require_row(evidence_id))

    async def list_by_work_package(
        self, work_package_id: WorkPackageId
    ) -> tuple[EvidenceRecord, ...]:
        """Returns every Evidence record attached to ``work_package_id``.

        This is the query behind the ``evidence`` fact of the ``RuleContext``
        (ADR-004 4.4). Assembling that context is Checkpoint 6's job, not this
        repository's.
        """
        rows = await self._rows_where(
            EvidenceRecordRow.work_package_id == work_package_id,
            order_by=EvidenceRecordRow.created_at,
        )
        return tuple(to_domain_evidence(row) for row in rows)

    async def list_by_qa_report(self, qa_report_id: QAReportId) -> tuple[EvidenceRecord, ...]:
        """Returns every Evidence record attached to ``qa_report_id``."""
        rows = await self._rows_where(
            EvidenceRecordRow.qa_report_id == qa_report_id,
            order_by=EvidenceRecordRow.created_at,
        )
        return tuple(to_domain_evidence(row) for row in rows)
