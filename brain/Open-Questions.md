# Open Questions

## Purpose

Track unresolved project questions.

## Questions

<!-- Placeholder -->

### What counts as evidence?

Status: Unresolved design question.

Examples discussed:

- Git diff
- Test output
- Screenshot
- API response
- Database query
- Logs

### How should Coordinators communicate?

Status: Open

Possible options discussed:

- Through the Orchestrator only.
- Direct Coordinator-to-Coordinator communication.
- Shared task queue.

No decision has been made.

### How should Features be decomposed into Tasks?

Goal
↓

Feature
↓

Tasks

The exact rules for Task decomposition remain open.

Status: Open

### What fields should a Work Package contain?

Status: Open

Notes:

We know a Work Package is the handover object between stages.

The exact structure has not yet been designed.

### What evidence is sufficient to prove work?

Status: Open

Notes:

The system currently defines the acceptance flow.

The exact evidence required by Backend, Frontend, QA, Review, and Coordinators remains undefined.

This will become the focus of the next checkpoint.

### How should the Orchestrator's knowledge and context be provided?

Status: Open

Notes:

The Orchestrator's decision and escalation flow has now been defined.

The mechanism for providing the Orchestrator with the appropriate organizational knowledge, engineering standards, and context has not yet been designed.

This will be addressed in a future checkpoint.

### What happens to a Feature's own status when its Feature Plan is superseded?

Status: Open. Narrowed 2026-08-25.

Source: [ADR-003](../adr/ADR-003.md) 3.13, and Questions Not Decided In The Checkpoint 2 Record (3).

Notes:

ADR-003 3.13 resolved the routing of a superseded Feature Plan and its Tasks. See Resolution Notes.

It did not decide what happens to the Feature's own lifecycle status when its plan is superseded, or how the successor plan revision is instantiated.

Design Session 009 is silent on both.

Relevant to Checkpoint 6.

### Deferred capabilities recorded by ADR-003

Status: Deferred, not rejected.

Notes:

These remain part of the architecture of record. They are not implemented in Foundation v1.

- D-1: Escalation blocking and the BLOCKED lifecycle state (Design Session 008). Must be designed explicitly before implementation.
- D-2: Coordinator lifecycle PROPOSED to APPROVED to ACTIVE to SUSPENDED to RETIRED (Design Session 009). Must be resolved before the Domain Registry is implemented.
- D-3: Domain Registry and the Builder-approval registration workflow (Design Session 009). Same gate as D-2.
- D-4: Feature Plan supersession from DRAFT or READY. Not required by Foundation v1.
- D-5: QA severity and priority classification taxonomy (Design Session 004). Not required by Foundation v1.
- D-6: Task stop and abandon lifecycle, and the persisted record of a Coordinator disposition decision, including any recorded relationship between a superseded plan's Task and successor planned work (ADR-003 3.13). Must be designed explicitly before any post-supersession disposition is implemented.

## Resolution Notes

Questions removed from the list above, with the decision that resolved each one.

### Does a QA defect need an explicit in-scope marker?

Status: Resolved 2026-08-25.

Resolved by: [ADR-003](../adr/ADR-003.md) 3.11.

Notes:

No. A defect's scope is never declared by QA. It is derived by the OS from an explicit structural association: the defect references the Task it was found against, or the Feature directly when no Task represents the affected capability.

The OS resolves Defect to Task to Feature, validates that the chain reaches the Feature under validation, and rejects any Feature Acceptance resting on a QA Final Pass that carries a defect whose scope cannot be resolved.

The OS enforces the integrity of the relationship, not the judgement behind it. Feature.in_scope remains free text and is never text-matched against a defect.

### When are Tasks instantiated in the OS?

Status: Resolved 2026-08-25.

Resolved by: [ADR-003](../adr/ADR-003.md) 3.12.

Notes:

Tasks may be created while the Feature Plan is still DRAFT. Existence confers no execution authority.

Execution authorization derives from the originating Feature Plan reaching ACTIVE, and is enforced on the transition to READY.

A Task existing is not a Task being authorized to execute. Design Session 007 is unchanged: its protection is preserved by the authorization gate rather than by delaying creation.

### What happens to a Feature when its Feature Plan is superseded?

Status: Resolved in part 2026-08-25. Residual question carried forward under Questions.

Resolved by: [ADR-003](../adr/ADR-003.md) 3.13.

Notes:

Resolved for the Plan and its Tasks. The old Plan and its Tasks remain immutable history. Tasks are not moved, not deleted, and not automatically halted. The Coordinator explicitly decides the disposition of each unfinished Task: resume, reuse, abandon, or redirect. Useful work may be represented as new planned work in the successor plan. No automatic migration mechanism exists or may be built.

Not resolved for the Feature itself. See "What happens to a Feature's own status when its Feature Plan is superseded?" under Questions.
