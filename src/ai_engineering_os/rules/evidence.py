"""Mandatory System Evidence rules — evaluation stage 4 (ADR-004 4.9, 4.10).

Evidence requirements are defined by the OS. Workers never decide the minimum,
and every Worker type follows a predefined Evidence Standard (Design Session
005). The standard is keyed off ``Task.capability`` (ADR-003 3.7) and **never**
off ``Claim.claim_type``, which is a descriptive label serving Reviewer Stage 2
judgement rather than deterministic enforcement.
"""

from collections.abc import Mapping
from types import MappingProxyType

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.enums import CapabilityType, EvidenceSourceType, EvidenceType
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult

__all__ = ["MANDATORY_SYSTEM_EVIDENCE", "SystemEvidenceRequiredRule"]

MANDATORY_SYSTEM_EVIDENCE: Mapping[CapabilityType, tuple[EvidenceType, ...]] = MappingProxyType(
    {
        CapabilityType.BACKEND: (
            EvidenceType.GIT_DIFF,
            EvidenceType.TEST_OUTPUT,
            EvidenceType.API_RESPONSE,
        ),
    }
)
"""The Foundation v1 minimum System Evidence standard, by capability.

Design Session 005 specifies the **Backend Worker only**. No standard is
invented for ``FRONTEND`` or ``QA``; a capability absent from this table fails
closed (ADR-004 4.9).

``DB_VERIFICATION`` is deliberately excluded. Design Session 005 requires it
"when applicable", and applicability is engineering judgement that Design
Session 005 assigns to the Reviewer at Stage 2. Encoding it as a deterministic
requirement would mean inventing an applicability rule the architecture has not
ruled (Blueprint 14.2 item 13).
"""


class SystemEvidenceRequiredRule(Rule):
    """The mandatory System Evidence for the Task's capability must be attached.

    Only ``SYSTEM`` evidence counts toward the minimum: Worker Evidence explains
    the work but is never independently verified, so it cannot discharge a
    requirement that exists to provide independent verification (ADR-001).

    Two distinct codes are emitted so a rejection never falsely blames the
    Worker for a gap in the OS:

    - ``MISSING_SYSTEM_EVIDENCE`` — the Worker omitted required evidence.
    - ``EVIDENCE_STANDARD_UNDEFINED`` — the OS has not ruled the standard.

    An undefined standard is **never** treated as "no evidence required".
    Failing open would silently reduce Design Session 005's "Workers may never
    provide less than the required minimum" to no minimum at all.
    """

    rule_id = RuleId.SYSTEM_EVIDENCE_REQUIRED
    condition = TransitionCondition.MANDATORY_SYSTEM_EVIDENCE_ATTACHED
    stage = RuleStage.EVIDENCE
    required_facts = frozenset({RuleFact.TASK, RuleFact.EVIDENCE})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the capability's mandatory System Evidence is present."""
        task = context.require_task()
        required = MANDATORY_SYSTEM_EVIDENCE.get(task.capability)

        if required is None:
            return self.failed(
                RuleCode.EVIDENCE_STANDARD_UNDEFINED,
                f"No mandatory System Evidence standard has been ruled for capability "
                f"{task.capability}; the OS fails closed rather than requiring nothing",
                RuleDetail.of("capability", [task.capability]),
                RuleDetail.of("defined_standards", sorted(MANDATORY_SYSTEM_EVIDENCE)),
                RuleDetail.of("task_id", [task.id]),
            )

        attached = {
            record.evidence_type
            for record in context.require_evidence()
            if record.source_type is EvidenceSourceType.SYSTEM
        }
        missing = tuple(kind for kind in required if kind not in attached)
        if missing:
            return self.failed(
                RuleCode.MISSING_SYSTEM_EVIDENCE,
                f"Task {task.id} is missing {len(missing)} mandatory System Evidence record(s) "
                f"for capability {task.capability}",
                RuleDetail.of("required_evidence", required),
                RuleDetail.of("missing_evidence", missing),
                RuleDetail.of("capability", [task.capability]),
                RuleDetail.of("task_id", [task.id]),
            )

        return self.passed(
            f"Task {task.id} carries every mandatory System Evidence record for "
            f"capability {task.capability}"
        )
