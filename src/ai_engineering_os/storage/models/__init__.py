"""SQLAlchemy ORM table definitions for AI Engineering OS (ADR-005).

Importing this package registers every table on ``Base.metadata``, which is what
``migrations/env.py`` relies on.

**These types never leave the storage layer** (ADR-005 5.11). Repositories return
frozen domain objects; the Rule Engine and every higher layer must never receive
a SQLAlchemy model.

`os_events` and `state_transitions_audit` are **not here**: both belong to
Checkpoint 5 (ADR-005 5.13).
"""

from ai_engineering_os.storage.database import Base
from ai_engineering_os.storage.models.actor import ActorRow
from ai_engineering_os.storage.models.decision import (
    DecisionAcknowledgementRow,
    DecisionRow,
    ReviewDecisionRow,
)
from ai_engineering_os.storage.models.evidence import EvidenceRecordRow
from ai_engineering_os.storage.models.feature import FeatureRow
from ai_engineering_os.storage.models.plan import FeaturePlanRow, PlanTaskDefinitionRow
from ai_engineering_os.storage.models.qa import QADefectRow, QAReportRow
from ai_engineering_os.storage.models.task import TaskDependencyRow, TaskRevisionRow, TaskRow
from ai_engineering_os.storage.models.work_package import (
    WORK_PACKAGE_CONTENT_COLUMNS,
    WorkPackageRow,
)

__all__ = [
    "WORK_PACKAGE_CONTENT_COLUMNS",
    "ActorRow",
    "Base",
    "DecisionAcknowledgementRow",
    "DecisionRow",
    "EvidenceRecordRow",
    "FeaturePlanRow",
    "FeatureRow",
    "PlanTaskDefinitionRow",
    "QADefectRow",
    "QAReportRow",
    "ReviewDecisionRow",
    "TaskDependencyRow",
    "TaskRevisionRow",
    "TaskRow",
    "WorkPackageRow",
]
