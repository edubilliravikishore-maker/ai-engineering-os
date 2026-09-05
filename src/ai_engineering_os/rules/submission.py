"""Work Package submission rules — evaluation stage 4 (ADR-004 4.3, 4.10).

Three rules governing Task ``IN_PROGRESS -> SUBMITTED`` (Blueprint 5.2). They
sit alongside ``SystemEvidenceRequiredRule`` in the evidence stage because they
ask the same kind of question: *did the Worker actually hand over what the OS
requires before anyone reviews this?*

Each is separate rather than folded into one "submission is complete" rule.
A missing Work Package, missing Claims and a missing Verification Guide are
three different omissions with three different remedies, and a Worker fixing a
submission should be told all of them at once.
"""

from ai_engineering_os.domain.conditions import TransitionCondition
from ai_engineering_os.domain.work_package import WorkPackage
from ai_engineering_os.rules.base import Rule
from ai_engineering_os.rules.codes import RuleCode, RuleId, RuleStage
from ai_engineering_os.rules.context import RuleContext, RuleFact
from ai_engineering_os.rules.results import RuleDetail, RuleResult
from ai_engineering_os.rules.selection import active_revision

__all__ = [
    "ClaimsDefinedRule",
    "VerificationGuidePresentRule",
    "WorkPackagePresentRule",
]


def _active_work_package(context: RuleContext) -> WorkPackage | None:
    """Returns the Work Package of the Task's active Revision, if there is one.

    Both lookups can legitimately come back empty — a Task before its first
    submission has no active Revision, and a Revision may exist without a Work
    Package. Neither is a missing fact, so neither raises.
    """
    task = context.require_task()
    revision = active_revision(task, context.require_task_revisions())
    if revision is None:
        return None
    for package in context.require_work_packages():
        if package.task_revision_id == revision.id:
            return package
    return None


def _no_work_package(rule: Rule, task_id: object) -> RuleResult:
    """Fails closed when the prerequisite rule's guarantee does not hold.

    ``WORK_PACKAGE_PRESENT`` is declared as a prerequisite of both dependent
    rules, so the engine skips them when it fails and this branch is
    unreachable through the engine. It exists because a rule evaluated directly
    must still refuse rather than raise, and because a guarantee that is only
    documented is a guarantee that eventually stops holding.
    """
    return rule.failed(
        RuleCode.NO_WORK_PACKAGE_SUBMITTED,
        f"Task {task_id} carries no Work Package on its active Revision",
        RuleDetail.of("task_id", [task_id]),
    )


class WorkPackagePresentRule(Rule):
    """The active Task Revision must carry a Work Package.

    The Work Package is the Worker's handover object. Without one there is
    nothing for a Reviewer to review, and the Task would enter review on the
    strength of a status change alone.
    """

    rule_id = RuleId.WORK_PACKAGE_PRESENT
    condition = TransitionCondition.WORK_PACKAGE_PRESENT
    stage = RuleStage.EVIDENCE
    required_facts = frozenset({RuleFact.TASK, RuleFact.TASK_REVISIONS, RuleFact.WORK_PACKAGES})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the active Revision carries a Work Package."""
        task = context.require_task()
        revision = active_revision(task, context.require_task_revisions())

        if revision is None:
            return self.failed(
                RuleCode.NO_ACTIVE_REVISION,
                f"Task {task.id} has no active Revision, so nothing has been handed over",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("active_revision_number", [task.active_revision_number]),
            )

        package = _active_work_package(context)
        if package is None:
            return self.failed(
                RuleCode.NO_WORK_PACKAGE_SUBMITTED,
                f"Task Revision {revision.id} carries no Work Package",
                RuleDetail.of("task_id", [task.id]),
                RuleDetail.of("task_revision_id", [revision.id]),
            )

        return self.passed(f"Task {task.id} carries Work Package {package.id}")


class ClaimsDefinedRule(Rule):
    """The Work Package must declare at least one Claim.

    Blueprint 5.2. A Claim is what the Worker asserts they did; evidence
    supports Claims. A handover asserting nothing gives a Reviewer nothing to
    verify against.
    """

    rule_id = RuleId.CLAIMS_DEFINED
    condition = TransitionCondition.CLAIMS_DEFINED
    stage = RuleStage.EVIDENCE
    required_facts = frozenset({RuleFact.TASK, RuleFact.TASK_REVISIONS, RuleFact.WORK_PACKAGES})
    requires = frozenset({RuleId.WORK_PACKAGE_PRESENT})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the Work Package declares Claims."""
        task = context.require_task()
        package = _active_work_package(context)
        if package is None:
            return _no_work_package(self, task.id)

        if not package.claims:
            return self.failed(
                RuleCode.NO_CLAIMS_DECLARED,
                f"Work Package {package.id} declares no Claim",
                RuleDetail.of("work_package_id", [package.id]),
                RuleDetail.of("task_id", [task.id]),
            )

        return self.passed(f"Work Package {package.id} declares {len(package.claims)} Claim(s)")


class VerificationGuidePresentRule(Rule):
    """The Work Package must carry a Verification Guide.

    Blueprint 5.2. The Guide is how a Reviewer and QA reproduce the Worker's
    result. Without it, verification depends on the Reviewer guessing what to
    run, which is the opposite of the reproducibility the OS exists to enforce.
    """

    rule_id = RuleId.VERIFICATION_GUIDE_PRESENT
    condition = TransitionCondition.VERIFICATION_GUIDE_PRESENT
    stage = RuleStage.EVIDENCE
    required_facts = frozenset({RuleFact.TASK, RuleFact.TASK_REVISIONS, RuleFact.WORK_PACKAGES})
    requires = frozenset({RuleId.WORK_PACKAGE_PRESENT})

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Returns whether the Work Package carries a Verification Guide."""
        task = context.require_task()
        package = _active_work_package(context)
        if package is None:
            return _no_work_package(self, task.id)

        if package.verification_guide is None:
            return self.failed(
                RuleCode.NO_VERIFICATION_GUIDE,
                f"Work Package {package.id} carries no Verification Guide",
                RuleDetail.of("work_package_id", [package.id]),
                RuleDetail.of("task_id", [task.id]),
            )

        return self.passed(f"Work Package {package.id} carries a Verification Guide")
