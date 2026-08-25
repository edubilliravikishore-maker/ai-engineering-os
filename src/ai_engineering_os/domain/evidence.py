"""Evidence records (Blueprint 4.1 #6, Design Session 005).

Evidence proves that the Claims inside a Work Package are true. System Evidence
is generated independently by the OS and carries the highest trust; Worker
Evidence explains the work but is never independently verified.
"""

import hashlib
from datetime import datetime

from pydantic import Field, model_validator

from ai_engineering_os.domain.base import DomainModel, NonEmptyText, Sha256Hex, utc_now
from ai_engineering_os.domain.enums import EvidenceSourceType, EvidenceType
from ai_engineering_os.domain.identifiers import EvidenceId, QAReportId, WorkPackageId

__all__ = ["EvidenceMetadata", "EvidenceRecord", "sha256_hex"]


def sha256_hex(payload: str) -> str:
    """Returns the lowercase hexadecimal SHA-256 digest of ``payload``."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class EvidenceMetadata(DomainModel):
    """Reproduction context recorded alongside an Evidence record."""

    command: NonEmptyText | None = None
    exit_code: int | None = None
    git_hash: NonEmptyText | None = None
    timestamp: datetime | None = None


class EvidenceRecord(DomainModel):
    """A durable, integrity-verifiable record supporting a Claim or QA result.

    ``content`` holds the evidence itself, or a durable URI reference when the
    payload exceeds the configured inline threshold. ``checksum`` is always the
    authoritative SHA-256 digest of the underlying payload.
    """

    id: EvidenceId
    source_type: EvidenceSourceType
    evidence_type: EvidenceType
    content: NonEmptyText
    checksum: Sha256Hex
    work_package_id: WorkPackageId | None = None
    qa_report_id: QAReportId | None = None
    metadata: EvidenceMetadata = Field(default_factory=EvidenceMetadata)
    verified_by_os: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _evidence_must_be_attached(self) -> "EvidenceRecord":
        """Evidence exists to support a Work Package or a QA Report, never alone."""
        if self.work_package_id is None and self.qa_report_id is None:
            raise ValueError("An Evidence record must reference a Work Package or a QA Report")
        return self

    @model_validator(mode="after")
    def _worker_evidence_is_never_os_verified(self) -> "EvidenceRecord":
        """Design Session 005: only independently generated evidence is OS-verified."""
        if self.source_type is EvidenceSourceType.WORKER and self.verified_by_os:
            raise ValueError("Worker Evidence cannot be marked as independently verified by the OS")
        return self

    @property
    def is_system_evidence(self) -> bool:
        """Returns whether this record is mandatory, independently generated evidence."""
        return self.source_type is EvidenceSourceType.SYSTEM

    def verify_integrity(self, payload: str) -> bool:
        """Returns whether ``payload`` matches the recorded authoritative checksum."""
        return sha256_hex(payload) == self.checksum

    @classmethod
    def for_inline_content(
        cls,
        *,
        id: EvidenceId,
        source_type: EvidenceSourceType,
        evidence_type: EvidenceType,
        content: str,
        work_package_id: WorkPackageId | None = None,
        qa_report_id: QAReportId | None = None,
        metadata: EvidenceMetadata | None = None,
        verified_by_os: bool = False,
        created_at: datetime | None = None,
    ) -> "EvidenceRecord":
        """Builds an Evidence record whose checksum is derived from inline content."""
        return cls(
            id=id,
            source_type=source_type,
            evidence_type=evidence_type,
            content=content,
            checksum=sha256_hex(content),
            work_package_id=work_package_id,
            qa_report_id=qa_report_id,
            metadata=metadata or EvidenceMetadata(),
            verified_by_os=verified_by_os,
            created_at=created_at or utc_now(),
        )
