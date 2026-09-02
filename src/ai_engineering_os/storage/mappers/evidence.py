"""Evidence record <-> row mapping.

``metadata`` is a reserved attribute name on the SQLAlchemy declarative base, so
the column is named ``evidence_metadata``. The domain field name is unchanged.
"""

from ai_engineering_os.domain.evidence import EvidenceRecord
from ai_engineering_os.storage.mappers.base import reconstruct
from ai_engineering_os.storage.models.evidence import EvidenceRecordRow

__all__ = ["to_domain_evidence", "to_evidence_row"]


def to_domain_evidence(row: EvidenceRecordRow) -> EvidenceRecord:
    """Rebuilds the immutable Evidence record recorded by ``row``."""
    return reconstruct(
        EvidenceRecord,
        {
            "id": row.id,
            "source_type": row.source_type,
            "evidence_type": row.evidence_type,
            "content": row.content,
            "checksum": row.checksum,
            "work_package_id": row.work_package_id,
            "qa_report_id": row.qa_report_id,
            "metadata": row.evidence_metadata,
            "verified_by_os": row.verified_by_os,
            "created_at": row.created_at,
        },
        entity_id=row.id,
    )


def to_evidence_row(evidence: EvidenceRecord) -> EvidenceRecordRow:
    """Builds the append-only row recording ``evidence``."""
    return EvidenceRecordRow(
        id=evidence.id,
        source_type=evidence.source_type.value,
        evidence_type=evidence.evidence_type.value,
        content=evidence.content,
        checksum=evidence.checksum,
        work_package_id=evidence.work_package_id,
        qa_report_id=evidence.qa_report_id,
        evidence_metadata=evidence.metadata.model_dump(mode="json"),
        verified_by_os=evidence.verified_by_os,
        created_at=evidence.created_at,
    )
