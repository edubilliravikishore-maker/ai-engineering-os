"""Strongly typed identifiers for AI Engineering OS domain entities.

Every entity in the blueprint domain model is identified by a UUID. Wrapping
those UUIDs in distinct ``NewType`` aliases prevents accidentally passing a
``TaskId`` where a ``FeatureId`` is required, without introducing runtime cost.
"""

from collections.abc import Callable
from typing import NewType
from uuid import UUID, uuid4

__all__ = [
    "ActorId",
    "ClaimId",
    "DecisionId",
    "EvidenceId",
    "FeatureId",
    "FeaturePlanId",
    "QADefectId",
    "QAReportId",
    "ReviewDecisionId",
    "TaskId",
    "TaskRevisionId",
    "WorkPackageId",
    "new_id",
]

ActorId = NewType("ActorId", UUID)
ClaimId = NewType("ClaimId", UUID)
DecisionId = NewType("DecisionId", UUID)
EvidenceId = NewType("EvidenceId", UUID)
FeatureId = NewType("FeatureId", UUID)
FeaturePlanId = NewType("FeaturePlanId", UUID)
QADefectId = NewType("QADefectId", UUID)
QAReportId = NewType("QAReportId", UUID)
ReviewDecisionId = NewType("ReviewDecisionId", UUID)
TaskId = NewType("TaskId", UUID)
TaskRevisionId = NewType("TaskRevisionId", UUID)
WorkPackageId = NewType("WorkPackageId", UUID)


def new_id[IdT](identifier: Callable[[UUID], IdT]) -> IdT:
    """Returns a freshly generated UUID wrapped in the given identifier type."""
    return identifier(uuid4())
