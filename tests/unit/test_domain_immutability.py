"""Unit tests for the additive-history and immutability semantics of the domain.

The architecture requires that history is never rewritten: Task Revisions are
strictly additive, submitted Work Packages are immutable, Evidence preserves its
integrity, and Decisions preserve their acknowledgement history.
"""

import pytest
from pydantic import ValidationError

from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    Claim,
    Decision,
    DecisionId,
    DecisionScope,
    EvidenceRecord,
    Feature,
    FeatureStatus,
    ImmutableRecordError,
    InvariantViolationError,
    RevisionSequenceError,
    Task,
    TaskId,
    TaskRevision,
    TaskRevisionHistory,
    TaskRevisionId,
    TaskStatus,
    VerificationGuide,
    WorkPackage,
    WorkPackageId,
    WorkPackageStatus,
    new_id,
    utc_now,
)


def _revision(task: Task, worker_id: ActorId, number: int) -> TaskRevision:
    return TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=task.id,
        revision_number=number,
        created_by_worker_id=worker_id,
    )


# --------------------------------------------------------------------------
# Frozen models
# --------------------------------------------------------------------------


def test_domain_models_are_frozen(feature: Feature, task: Task) -> None:
    """Verifies domain records cannot be mutated in place."""
    with pytest.raises(ValidationError):
        feature.status = FeatureStatus.ACCEPTED  # type: ignore[misc]
    with pytest.raises(ValidationError):
        task.title = "Renamed"  # type: ignore[misc]


def test_state_change_produces_a_new_record(feature: Feature) -> None:
    """Verifies a status change never mutates the original record."""
    planned = feature.with_status(FeatureStatus.PLANNED)
    assert planned is not feature
    assert feature.status is FeatureStatus.DRAFT
    assert planned.status is FeatureStatus.PLANNED


def test_collections_are_immutable_sequences(feature: Feature, backend_worker: Actor) -> None:
    """Verifies recorded lists are tuples/frozensets rather than mutable containers."""
    assert isinstance(feature.in_scope, tuple)
    assert isinstance(feature.acceptance_criteria, tuple)
    assert isinstance(backend_worker.capabilities, frozenset)


# --------------------------------------------------------------------------
# Task Revision history (additive)
# --------------------------------------------------------------------------


def test_revision_history_starts_empty(task: Task) -> None:
    """Verifies a Task begins with no Revision and expects Revision 1 next."""
    history = TaskRevisionHistory(task_id=task.id)
    assert history.revisions == ()
    assert history.active_revision is None
    assert history.next_revision_number == 1


def test_appending_revisions_preserves_history(task: Task, worker_id: ActorId) -> None:
    """Verifies Design Session 006: history is preserved, never replaced."""
    history = TaskRevisionHistory(task_id=task.id)
    first = _revision(task, worker_id, 1)
    second = _revision(task, worker_id, 2)

    after_first = history.append(first)
    after_second = after_first.append(second)

    assert history.revisions == ()
    assert len(after_first.revisions) == 1
    assert len(after_second.revisions) == 2
    assert after_second.revision(1) is first
    assert after_second.revision(2) is second


def test_appending_does_not_rewrite_recorded_revisions(task: Task, worker_id: ActorId) -> None:
    """Verifies ADR-003 3.1: an appended Revision never re-marks recorded history."""
    first = _revision(task, worker_id, 1)
    second = _revision(task, worker_id, 2)
    history = TaskRevisionHistory(task_id=task.id).append(first).append(second)

    assert history.revisions[0] is first
    assert history.revisions[1] is second


def test_active_revision_is_derived_from_the_history_head(task: Task, worker_id: ActorId) -> None:
    """Verifies Design Session 006's single active Revision is derived, not stored."""
    history = (
        TaskRevisionHistory(task_id=task.id)
        .append(_revision(task, worker_id, 1))
        .append(_revision(task, worker_id, 2))
    )
    assert history.active_revision is not None
    assert history.active_revision.revision_number == 2
    assert not hasattr(history.active_revision, "status")


def test_history_consistency_follows_the_task_active_revision_pointer(
    task: Task, worker_id: ActorId
) -> None:
    """Verifies Task.active_revision_number is the authoritative active pointer."""
    history = TaskRevisionHistory(task_id=task.id).append(_revision(task, worker_id, 1))
    assigned = task.with_status(TaskStatus.READY).assign(worker_id)

    assert history.is_consistent_with(assigned.with_active_revision(1))
    assert not history.is_consistent_with(assigned)


def test_revision_numbers_must_increment_by_one(task: Task, worker_id: ActorId) -> None:
    """Verifies revision history is strictly additive."""
    history = TaskRevisionHistory(task_id=task.id).append(_revision(task, worker_id, 1))
    with pytest.raises(RevisionSequenceError) as excinfo:
        history.append(_revision(task, worker_id, 3))
    assert excinfo.value.expected_revision_number == 2
    assert excinfo.value.received_revision_number == 3
    assert excinfo.value.code == "REVISION_SEQUENCE"


def test_existing_revision_cannot_be_overwritten(task: Task, worker_id: ActorId) -> None:
    """Verifies a Worker cannot replace an already recorded Revision."""
    history = TaskRevisionHistory(task_id=task.id).append(_revision(task, worker_id, 1))
    with pytest.raises(RevisionSequenceError):
        history.append(_revision(task, worker_id, 1))


def test_revision_from_another_task_is_rejected(task: Task, worker_id: ActorId) -> None:
    """Verifies revision history never mixes Task identities."""
    history = TaskRevisionHistory(task_id=task.id)
    foreign = TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=new_id(TaskId),
        revision_number=1,
        created_by_worker_id=worker_id,
    )
    with pytest.raises(ImmutableRecordError) as excinfo:
        history.append(foreign)
    assert excinfo.value.code == "IMMUTABLE_RECORD"
    assert excinfo.value.record_type == "TaskRevisionHistory"


def test_history_rejects_non_contiguous_construction(task: Task, worker_id: ActorId) -> None:
    """Verifies a history cannot be constructed with gaps."""
    with pytest.raises(ValidationError, match="contiguous"):
        TaskRevisionHistory(
            task_id=task.id,
            revisions=(_revision(task, worker_id, 1), _revision(task, worker_id, 3)),
        )


def test_task_active_revision_pointer_only_moves_forward(task: Task, worker_id: ActorId) -> None:
    """Verifies a Task cannot point back at an earlier Revision."""
    assigned = task.with_status(TaskStatus.READY).assign(worker_id)
    with_revision = assigned.with_active_revision(1)
    assert with_revision.active_revision_number == 1
    with pytest.raises(RevisionSequenceError):
        with_revision.with_active_revision(1)


# --------------------------------------------------------------------------
# Work Package immutability
# --------------------------------------------------------------------------


def test_draft_work_package_is_editable(draft_work_package: WorkPackage) -> None:
    """Verifies a DRAFT Work Package is still Worker-local content."""
    assert draft_work_package.is_draft
    assert not draft_work_package.is_immutable
    revised = draft_work_package.revise_draft(summary="Revised summary")
    assert revised.summary == "Revised summary"
    assert draft_work_package.summary != "Revised summary"


def test_submitted_work_package_cannot_be_edited(
    draft_work_package: WorkPackage, claim: Claim, verification_guide: VerificationGuide
) -> None:
    """Verifies Design Session 003: a submitted Work Package is immutable."""
    submitted = draft_work_package.revise_draft(
        claims=(claim,), verification_guide=verification_guide
    ).submit(at=utc_now())

    assert submitted.status is WorkPackageStatus.SUBMITTED
    assert submitted.is_immutable
    with pytest.raises(ImmutableRecordError) as excinfo:
        submitted.revise_draft(summary="Sneaky edit")
    assert excinfo.value.record_type == "WorkPackage"
    assert excinfo.value.operation == "revise_draft"


def test_submitted_work_package_cannot_be_resubmitted(
    draft_work_package: WorkPackage, claim: Claim, verification_guide: VerificationGuide
) -> None:
    """Verifies a submitted package is never re-submitted in place."""
    submitted = draft_work_package.revise_draft(
        claims=(claim,), verification_guide=verification_guide
    ).submit(at=utc_now())
    with pytest.raises(ImmutableRecordError):
        submitted.submit(at=utc_now())


def test_status_changes_do_not_go_through_draft_revision(
    draft_work_package: WorkPackage,
) -> None:
    """Verifies lifecycle status is never smuggled in as a content edit."""
    with pytest.raises(ImmutableRecordError, match="with_status"):
        draft_work_package.revise_draft(status=WorkPackageStatus.SUBMITTED)


def test_lifecycle_status_change_preserves_recorded_content(
    draft_work_package: WorkPackage, claim: Claim, verification_guide: VerificationGuide
) -> None:
    """Verifies advancing the Work Package lifecycle never alters its content."""
    submitted = draft_work_package.revise_draft(
        claims=(claim,), verification_guide=verification_guide
    ).submit(at=utc_now())
    validated = submitted.with_status(WorkPackageStatus.VALIDATED)
    assert validated.summary == submitted.summary
    assert validated.claims == submitted.claims
    assert validated.verification_guide == submitted.verification_guide
    assert validated.submitted_at == submitted.submitted_at


def test_fixing_work_requires_a_new_work_package(
    draft_work_package: WorkPackage, claim: Claim, verification_guide: VerificationGuide
) -> None:
    """Verifies fixes produce a new Work Package rather than editing the old one."""
    submitted = draft_work_package.revise_draft(
        claims=(claim,), verification_guide=verification_guide
    ).submit(at=utc_now())
    replacement = WorkPackage(
        id=new_id(WorkPackageId),
        task_revision_id=submitted.task_revision_id,
        summary="Second attempt after review feedback",
    )
    assert replacement.id != submitted.id
    assert replacement.is_draft


# --------------------------------------------------------------------------
# Evidence integrity
# --------------------------------------------------------------------------


def test_evidence_record_is_immutable(system_evidence: EvidenceRecord) -> None:
    """Verifies an Evidence record preserves its identity and integrity."""
    with pytest.raises(ValidationError):
        system_evidence.content = "tampered"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        system_evidence.checksum = "0" * 64  # type: ignore[misc]


def test_tampered_evidence_fails_integrity_verification(
    system_evidence: EvidenceRecord,
) -> None:
    """Verifies the recorded checksum detects a content substitution."""
    tampered = system_evidence._evolve(content="rewritten history")
    assert not tampered.verify_integrity(tampered.content)


# --------------------------------------------------------------------------
# Decision history
# --------------------------------------------------------------------------


def _system_decision(actor: ActorId) -> Decision:
    return Decision(
        id=new_id(DecisionId),
        scope=DecisionScope.SYSTEM,
        decided_by_role=ActorRole.ORCHESTRATOR,
        decided_by_id=actor,
        problem="Two domains need a shared session contract",
        decision_text="Adopt a single shared session token format",
        reasoning="Avoids duplicate contracts across domains",
        alternatives_considered=("Per-domain session formats",),
        affected_domains=("auth-domain", "payments-domain"),
    )


def test_acknowledgement_is_additive() -> None:
    """Verifies Design Session 008: acknowledgements accumulate on the Decision."""
    decision = _system_decision(new_id(ActorId))
    coordinator = new_id(ActorId)
    acknowledged = decision.acknowledge(actor_id=coordinator, actor_role=ActorRole.COORDINATOR)

    assert decision.acknowledgements == ()
    assert len(acknowledged.acknowledgements) == 1
    assert acknowledged.is_acknowledged_by(coordinator)
    assert not decision.is_acknowledged_by(coordinator)


def test_second_acknowledgement_by_another_actor_is_preserved() -> None:
    """Verifies each acknowledging Coordinator is recorded independently."""
    first = new_id(ActorId)
    second = new_id(ActorId)
    decision = (
        _system_decision(new_id(ActorId))
        .acknowledge(actor_id=first, actor_role=ActorRole.COORDINATOR)
        .acknowledge(actor_id=second, actor_role=ActorRole.COORDINATOR)
    )
    assert [ack.actor_id for ack in decision.acknowledgements] == [first, second]


def test_duplicate_acknowledgement_is_rejected() -> None:
    """Verifies acknowledgement history is not silently overwritten."""
    coordinator = new_id(ActorId)
    decision = _system_decision(new_id(ActorId)).acknowledge(
        actor_id=coordinator, actor_role=ActorRole.COORDINATOR
    )
    with pytest.raises(InvariantViolationError) as excinfo:
        decision.acknowledge(actor_id=coordinator, actor_role=ActorRole.COORDINATOR)
    assert excinfo.value.code == "INVARIANT_VIOLATION"


def test_decision_record_is_immutable() -> None:
    """Verifies a recorded Decision cannot be rewritten in place."""
    decision = _system_decision(new_id(ActorId))
    with pytest.raises(ValidationError):
        decision.decision_text = "Something else"  # type: ignore[misc]
