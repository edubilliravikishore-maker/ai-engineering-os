"""Entity repositories (ADR-005 5.4, 5.11).

Every repository here **returns domain objects**. A SQLAlchemy model never
crosses this boundary, so the Rule Engine and every higher layer receive frozen
domain objects and nothing that carries a live session with it.

Two classes of repository, matching the two classes of table (ADR-005 5.8):

* **Mutable state** — Actor, Feature, Feature Plan, Task, and the hybrid Work
  Package. These expose ``save``, which writes under optimistic locking.
* **Append-only history** — Task Revision, Evidence, QA Report, Review Decision,
  Decision, and — as of Checkpoint 5 — the event stream and the transition
  audit ledger. **None exposes an update method at all.**

**No repository exposes a delete** (ADR-005 5.7), and **none commits** — the
service/use-case layer owns the transaction boundary (ADR-005 5.5).
"""

from ai_engineering_os.storage.repositories.actor_repo import ActorRepository
from ai_engineering_os.storage.repositories.base import BaseRepository
from ai_engineering_os.storage.repositories.decision_repo import DecisionRepository
from ai_engineering_os.storage.repositories.event_repo import EventRepository
from ai_engineering_os.storage.repositories.evidence_repo import EvidenceRepository
from ai_engineering_os.storage.repositories.feature_repo import FeatureRepository
from ai_engineering_os.storage.repositories.plan_repo import FeaturePlanRepository
from ai_engineering_os.storage.repositories.qa_repo import QAReportRepository
from ai_engineering_os.storage.repositories.review_decision_repo import ReviewDecisionRepository
from ai_engineering_os.storage.repositories.task_repo import TaskRepository
from ai_engineering_os.storage.repositories.task_revision_repo import TaskRevisionRepository
from ai_engineering_os.storage.repositories.transition_audit_repo import TransitionAuditRepository
from ai_engineering_os.storage.repositories.work_package_repo import WorkPackageRepository

__all__ = [
    "ActorRepository",
    "BaseRepository",
    "DecisionRepository",
    "EventRepository",
    "EvidenceRepository",
    "FeaturePlanRepository",
    "FeatureRepository",
    "QAReportRepository",
    "ReviewDecisionRepository",
    "TaskRepository",
    "TaskRevisionRepository",
    "TransitionAuditRepository",
    "WorkPackageRepository",
]
