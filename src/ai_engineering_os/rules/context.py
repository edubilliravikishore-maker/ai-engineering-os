"""The typed, frozen fact context supplied to rules (ADR-004 4.4).

Rules receive **all** facts through a single frozen ``RuleContext`` assembled by
the caller. A rule may not access PostgreSQL, SQLAlchemy, a session, a
repository, the filesystem, the network, a clock, or a random source. A rule
that can fetch its own facts can fetch different facts on two identical calls,
which destroys reproducibility.

The context carries only fields that at least one registered rule consumes, and
every field is a frozen domain model or a tuple of them, so the fact graph is
immutable **in depth**, not merely at its surface.

``None`` means *not supplied*. An empty tuple means *supplied, and empty* — a
real fact with a real meaning (a Feature genuinely has no Tasks recorded). The
engine fails closed on the former and lets rules judge the latter.

The **context loader** — the component that reads facts from persistence and
assembles a context — is not part of Checkpoint 3. It belongs to the Checkpoint
6 Kernel, built on Checkpoint 4 repositories.
"""

from dataclasses import dataclass
from enum import StrEnum

from ai_engineering_os.domain.actor import Actor
from ai_engineering_os.domain.errors import RuleContextIncompleteError
from ai_engineering_os.domain.evidence import EvidenceRecord
from ai_engineering_os.domain.feature import Feature
from ai_engineering_os.domain.qa import QAReport
from ai_engineering_os.domain.task import Task

__all__ = ["RuleContext", "RuleFact"]


class RuleFact(StrEnum):
    """The facts a rule may declare that it requires.

    This vocabulary is closed and minimal. A fact exists only because a
    registered rule consumes it.
    """

    CANDIDATE_WORKER = "candidate_worker"
    TASK = "task"
    FEATURE = "feature"
    FEATURE_TASKS = "feature_tasks"
    REFERENCED_TASKS = "referenced_tasks"
    EVIDENCE = "evidence"
    QA_REPORTS = "qa_reports"


_COLLECTION_FACTS: frozenset[RuleFact] = frozenset(
    {RuleFact.FEATURE_TASKS, RuleFact.REFERENCED_TASKS, RuleFact.EVIDENCE, RuleFact.QA_REPORTS}
)


@dataclass(frozen=True, slots=True)
class RuleContext:
    """The complete set of facts one rule evaluation may consider.

    Attributes:
        candidate_worker: The Actor proposed for an assignment.
        task: The Task under evaluation.
        feature: The Feature under evaluation.
        feature_tasks: Every Task recorded against ``feature``.
        referenced_tasks: Tasks resolved from identifiers held elsewhere —
            a Task's declared dependencies, and the Tasks QA defects associate
            with. Supplying them is how the caller lets a rule resolve a
            reference without performing a lookup of its own.
        evidence: Evidence records attached to the artefact under evaluation.
        qa_reports: QA Reports recorded against ``feature``.
    """

    candidate_worker: Actor | None = None
    task: Task | None = None
    feature: Feature | None = None
    feature_tasks: tuple[Task, ...] | None = None
    referenced_tasks: tuple[Task, ...] | None = None
    evidence: tuple[EvidenceRecord, ...] | None = None
    qa_reports: tuple[QAReport, ...] | None = None

    def __post_init__(self) -> None:
        """Rejects a mutable collection, so immutability is structural."""
        for fact in sorted(_COLLECTION_FACTS):
            value = getattr(self, fact.value)
            if value is not None and not isinstance(value, tuple):
                raise TypeError(f"RuleContext fact {fact.value!r} must be an immutable tuple")

    def has(self, fact: RuleFact) -> bool:
        """Returns whether ``fact`` was supplied."""
        value: object = getattr(self, fact.value)
        return value is not None

    def missing(self, facts: frozenset[RuleFact]) -> tuple[RuleFact, ...]:
        """Returns the required facts this context does not supply, in a stable order."""
        return tuple(fact for fact in sorted(facts) if not self.has(fact))

    def require_candidate_worker(self) -> Actor:
        """Returns the candidate Worker, failing closed when it was not supplied."""
        if self.candidate_worker is None:
            raise _incomplete(RuleFact.CANDIDATE_WORKER)
        return self.candidate_worker

    def require_task(self) -> Task:
        """Returns the Task under evaluation, failing closed when it was not supplied."""
        if self.task is None:
            raise _incomplete(RuleFact.TASK)
        return self.task

    def require_feature(self) -> Feature:
        """Returns the Feature under evaluation, failing closed when it was not supplied."""
        if self.feature is None:
            raise _incomplete(RuleFact.FEATURE)
        return self.feature

    def require_feature_tasks(self) -> tuple[Task, ...]:
        """Returns the Feature's Tasks, failing closed when they were not supplied."""
        if self.feature_tasks is None:
            raise _incomplete(RuleFact.FEATURE_TASKS)
        return self.feature_tasks

    def require_referenced_tasks(self) -> tuple[Task, ...]:
        """Returns the referenced Tasks, failing closed when they were not supplied."""
        if self.referenced_tasks is None:
            raise _incomplete(RuleFact.REFERENCED_TASKS)
        return self.referenced_tasks

    def require_evidence(self) -> tuple[EvidenceRecord, ...]:
        """Returns the attached Evidence, failing closed when it was not supplied."""
        if self.evidence is None:
            raise _incomplete(RuleFact.EVIDENCE)
        return self.evidence

    def require_qa_reports(self) -> tuple[QAReport, ...]:
        """Returns the Feature's QA Reports, failing closed when they were not supplied."""
        if self.qa_reports is None:
            raise _incomplete(RuleFact.QA_REPORTS)
        return self.qa_reports


def _incomplete(fact: RuleFact) -> RuleContextIncompleteError:
    """Builds the fail-closed error raised when a rule reads an unsupplied fact.

    The engine validates required facts before any rule runs, so reaching this
    is a second, defence-in-depth guard rather than the primary check.
    """
    return RuleContextIncompleteError(
        f"The rule context does not supply the required fact {fact.value!r}",
        rule_id="",
        missing_facts=(fact.value,),
    )
