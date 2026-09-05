"""Evidence rules — evaluation stage 4 (ADR-004 4.9, 4.10; ADR-007 7.2).

Two standards live here and they answer different questions.

``MANDATORY_SYSTEM_EVIDENCE`` is **per Task, per capability**: what a Worker must
attach before their Task may be submitted. ``FEATURE_MANDATORY_EVIDENCE`` is a
**Feature-level floor** asked once at Acceptance. Neither changes the other, and
a Task satisfying the first does not by itself satisfy the second.

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
from ai_engineering_os.rules.selection import current_round_reports

__all__ = [
    "FEATURE_MANDATORY_EVIDENCE",
    "MANDATORY_SYSTEM_EVIDENCE",
    "FeatureEvidenceRequiredRule",
    "SystemEvidenceRequiredRule",
]

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


FEATURE_MANDATORY_EVIDENCE: tuple[EvidenceType, ...] = (
    EvidenceType.GIT_DIFF,
    EvidenceType.TEST_OUTPUT,
    EvidenceType.REASONING,
)
"""The Feature-level evidence floor for Acceptance (ADR-007 7.2).

Three kinds, in plain terms: something was built, something was tested, and
somebody recorded what was done and why.

**A floor, not a second per-Task standard.** ``MANDATORY_SYSTEM_EVIDENCE`` above
is unchanged and still governs Task submission per capability. This set is asked
of the Feature as a whole, once, at Acceptance.

``API_RESPONSE`` and ``DB_VERIFICATION`` are deliberately absent. Neither is true
of every Feature — a purely front-end Feature has no endpoint to call and no row
to verify — and requiring evidence that does not exist produces fabricated
records, which is worse than requiring nothing. ``BUILD_LOG`` is per-capability
infrastructure and already required where it applies.

Adding a fourth kind later is straightforward. **Removing one is not**, because
Features accepted under this set will not carry it, which is why the set is
confined to the three that are always true.
"""


class FeatureEvidenceRequiredRule(Rule):
    """A Feature must carry code, tests and reasoning before it is accepted.

    Blueprint 5.1 ``IN_VALIDATION -> ACCEPTED``, ruled by ADR-007 7.2. The
    condition existed from the start; no Feature-level required set did, which
    is why it sat in ``BLOCKED_CONDITIONS`` rather than in the backlog.

    **The evidence closure.** Evidence attached to the Work Packages of the
    Feature's Tasks, together with the Evidence attached to the Feature's
    **current-round** QA Reports (ADR-007 7.4). Evidence attached to a
    superseded round's report is history: it supported a verdict the Feature has
    since moved past, and counting it would let a Feature satisfy this gate on
    the strength of work that was subsequently reworked.

    **What this rule cannot do, stated rather than glossed.** It checks that a
    ``REASONING`` record exists and is non-empty. It cannot check that the
    reasoning is accurate, relevant, or worth reading. ADR-007 7.2 records the
    standard — plain English carrying the technical detail a reader needs — as a
    requirement on the author enforced by the Builder at review, and accepts the
    box-ticking failure mode with eyes open. Recording it here as something the
    OS enforces would be a false guarantee.
    """

    rule_id = RuleId.FEATURE_EVIDENCE_PRESENT
    condition = TransitionCondition.MANDATORY_EVIDENCE_PRESENT
    stage = RuleStage.EVIDENCE
    required_facts = frozenset({RuleFact.FEATURE, RuleFact.EVIDENCE, RuleFact.QA_REPORTS})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the Feature's evidence closure carries all three kinds."""
        feature = context.require_feature()
        current = {
            report.id for report in current_round_reports(feature, context.require_qa_reports())
        }

        closure = tuple(
            record
            for record in context.require_evidence()
            if record.qa_report_id is None or record.qa_report_id in current
        )
        present = {record.evidence_type for record in closure}
        missing = tuple(kind for kind in FEATURE_MANDATORY_EVIDENCE if kind not in present)

        if missing:
            return self.failed(
                RuleCode.MISSING_FEATURE_EVIDENCE,
                f"Feature {feature.id} is missing {len(missing)} mandatory evidence kind(s) "
                f"for Acceptance",
                RuleDetail.of("missing_evidence_types", missing),
                RuleDetail.of("required_evidence_types", FEATURE_MANDATORY_EVIDENCE),
                RuleDetail.of("present_evidence_types", sorted(present)),
                RuleDetail.of("qa_round", [feature.qa_round]),
                RuleDetail.of("feature_id", [feature.id]),
            )

        return self.passed(
            f"Feature {feature.id} carries all {len(FEATURE_MANDATORY_EVIDENCE)} mandatory "
            f"evidence kinds in QA round {feature.qa_round}"
        )
