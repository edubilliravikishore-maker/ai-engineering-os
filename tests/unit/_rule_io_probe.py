"""Runtime I/O probe for the rule layer (ADR-004 4.6).

Run as a subprocess by ``test_domain_isolation.py``. A CPython audit hook cannot
be uninstalled, so it is installed only after every fact is constructed; from
that point on it observes exactly the rule evaluation.

This file is deliberately not named ``test_*``: it is a probe, not a test case.
"""

import sys
from uuid import uuid4

from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    Feature,
    FeatureId,
    FeaturePlanId,
    Task,
    TaskId,
    TransitionCondition,
)
from ai_engineering_os.rules import RULE_ENGINE, RuleContext

WATCHED_PREFIXES = (
    "open",
    "socket.",
    "urllib.",
    "subprocess.",
    "os.system",
    "os.exec",
    "os.remove",
    "os.rename",
    "shutil.",
    "sqlite3.",
    "ftplib.",
    "http.client.",
    "tempfile.",
    "pickle.",
)

audited: list[str] = []


def _build_context() -> RuleContext:
    coordinator_id = ActorId(uuid4())
    feature = Feature(
        id=FeatureId(uuid4()),
        slug="user-authentication",
        title="User Authentication",
        goal="Allow users to sign in",
        coordinator_id=coordinator_id,
    )
    task = Task(
        id=TaskId(uuid4()),
        feature_id=feature.id,
        feature_plan_id=FeaturePlanId(uuid4()),
        plan_definition_key="auth-api",
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
    )
    worker = Actor(
        id=ActorId(uuid4()),
        role=ActorRole.WORKER,
        name="backend-worker-1",
        capabilities=frozenset({CapabilityType.BACKEND}),
    )
    reviewer = Actor(
        id=ActorId(uuid4()),
        role=ActorRole.REVIEWER,
        name="reviewer-1",
        capabilities=frozenset({CapabilityType.BACKEND}),
    )
    return RuleContext(
        candidate_worker=worker,
        candidate_reviewers=(reviewer,),
        requesting_actor=worker,
        task=task,
        task_revisions=(),
        feature=feature,
        feature_tasks=(task,),
        feature_plans=(),
        referenced_tasks=(),
        work_packages=(),
        review_decisions=(),
        evidence=(),
        qa_reports=(),
    )


def main() -> None:
    """Evaluates every condition under an audit hook and reports what was observed."""
    context = _build_context()
    conditions = list(TransitionCondition)

    def hook(event: str, args: object) -> None:  # noqa: ARG001
        if event.startswith(WATCHED_PREFIXES):
            audited.append(event)

    sys.addaudithook(hook)
    evaluation = RULE_ENGINE.evaluate(conditions, context)
    sys.stdout.write(f"results={len(evaluation.results)} audited_events={sorted(set(audited))}\n")


main()
