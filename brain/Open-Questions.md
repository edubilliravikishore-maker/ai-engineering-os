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

### Does a QA defect need an explicit in-scope marker?

Status: Open

Source: [ADR-003](../adr/ADR-003.md), Questions Explicitly Not Decided Here (1).

Notes:

Design Session 009 gates Feature Acceptance on "zero unresolved in-scope defects".

QADefect carries no in-scope marker, and Feature.in_scope is free text that a defect cannot be mechanically matched against.

The Checkpoint 3 QAInScopeZeroDefectRule cannot be written deterministically until this is resolved.

Must be resolved before Checkpoint 3.

### When are Tasks instantiated in the OS?

Status: Open

Source: [ADR-003](../adr/ADR-003.md), Questions Explicitly Not Decided Here (2).

Notes:

Design Session 007 states the Coordinator creates Tasks only when their dependencies are satisfied, and that Tasks are not created simply because they may be needed later.

The Implementation Blueprint requires Tasks to be instantiated at plan activation, with PENDING_DEPENDENCIES available to park them.

These describe different instantiation timings.

Must be resolved before Checkpoint 6.

### What happens to a Feature when its Feature Plan is superseded?

Status: Open

Source: [ADR-003](../adr/ADR-003.md), Questions Explicitly Not Decided Here (3).

Notes:

Design Session 009 does not state what happens to the Feature when its plan is superseded, or how the successor plan revision is instantiated.

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

## Resolution Notes

<!-- Placeholder -->
