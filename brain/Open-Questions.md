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

Status: Open. Narrowed 2026-08-25.

Notes:

The system currently defines the acceptance flow.

The exact evidence required by Backend, Frontend, QA, Review, and Coordinators remains undefined.

[ADR-004](../adr/ADR-004.md) 4.9 rules the OS behaviour when a standard is undefined; it does not define the missing standards.

- Backend mandatory System Evidence is the Design Session 005 set, expressed as GIT_DIFF, TEST_OUTPUT, and API_RESPONSE.
- FRONTEND and QA mandatory System Evidence standards are still undefined and were deliberately not invented.
- A capability with no approved standard fails closed with the stable code EVIDENCE_STANDARD_UNDEFINED. An undefined standard is never treated as no evidence required.
- DB_VERIFICATION is not part of the deterministic mandatory Checkpoint 3 evidence set. Design Session 005's "database verification when applicable" remains engineering judgement, and no applicability logic was invented.

Both the FRONTEND / QA standards and a deterministic DB_VERIFICATION applicability rule remain Open. See Implementation Blueprint section 14, items 12 and 13.

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

Unchanged by [ADR-004](../adr/ADR-004.md), which explicitly does not decide it. Still Open.

### Which conditions cannot yet have a Rule?

Status: Open. Raised 2026-08-25.

Source: [ADR-004](../adr/ADR-004.md) 4.11, and Implementation Blueprint section 14, items 15 to 17.

Notes:

Three declared transition conditions cannot be evaluated deterministically because the architecture has not defined what they mean. They are classified BLOCKED_CONDITIONS and must not be silently decided during implementation.

- ALL_IMPLEMENTATION_TASKS_ACCEPTED. "Implementation task" is undefined across Design Sessions 001 to 009, ADR-003, and the Blueprint.
- MANDATORY_EVIDENCE_PRESENT at Feature acceptance. No Feature-level required evidence set exists; Design Session 005's standards are per Worker type.
- REVIEWER_ASSIGNED. No domain concept exists. Task carries no reviewer and no routing model is defined.

All three are Foundation v1 required conditions under [ADR-004](../adr/ADR-004.md) 4.13, so all three block Checkpoint 6 under the safety gate of [ADR-004](../adr/ADR-004.md) 4.12.

### Which QA report states a Feature's current defect position?

Status: Open. Raised 2026-08-29 by the Checkpoint 3 audit.

Source: [ADR-004](../adr/ADR-004.md) 4.15, and Implementation Blueprint section 14.3, item 18.

Notes:

QA Reports are immutable audit history. An OPEN defect written into a superseded report stays OPEN in that record forever, so treating every historical report as a live acceptance blocker would make any Feature that ever failed QA permanently unacceptable, and would render the Design Session 009 rework loop IN_VALIDATION to IN_PROGRESS to ACCEPTED unreachable.

Nothing in the architecture identifies which QA Report states a Feature's current defect position.

Checkpoint 3 does not decide this, and the rule layer does not attempt to. Selecting the authoritative result and evaluating it are separate concerns owned by separate components. The future OS Kernel and context loader select which QA result is authoritative; the Rule Engine evaluates whatever facts the RuleContext supplies and takes no view on how many reports it receives.

Repeat QA is normal. A QA Report is scoped to a Task Revision, and the rework loop from IN_VALIDATION back to IN_PROGRESS produces more of them. Nothing in the approved architecture limits a Feature to one QA Report, so a rule that rejected a Feature merely because several reports were supplied would be inventing QA workflow semantics it does not own.

Nothing may be invented before this is designed: no recency ordering, no sequence number, no timestamp comparison, no latest marker, no current_report_id, no QA session identity, no persistence query, and no additional RuleContext fact.

Must be designed before Checkpoint 6, which owns the context loader that decides which QA Reports a rule sees.

Known limitation while this stays open: the correctness of ZERO_UNRESOLVED_IN_SCOPE_DEFECTS depends entirely on the caller supplying the right reports. Checkpoint 3 proves the ADR-003 3.11 derivation, not the end-to-end acceptance guarantee. This is recorded as a limitation, not claimed as enforcement.

### Can the OS verify that a defect's Feature association points at a real Feature?

Status: Open. Raised 2026-08-29 by the Checkpoint 3 audit.

Source: [ADR-004](../adr/ADR-004.md) 4.16, and Implementation Blueprint section 14.3, item 19.

Notes:

The approved seven-fact RuleContext supplies only the Feature under acceptance. An existing different Feature and a nonexistent Feature identifier are therefore indistinguishable to a rule, and both are treated as out of scope.

No known_feature_ids fact was added and no lookup was invented. Checkpoint 3 does not claim to validate Feature-reference existence.

A dangling Task association is detected, because the Task facts needed to check it are supplied. The asymmetry follows directly from the approved fact set rather than from an oversight.

Must be addressed when the persistence and context-loader layer is designed, at Checkpoints 4 and 6. No gate is set on Checkpoint 3.

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

[ADR-004](../adr/ADR-004.md) changes none of these. D-1 and D-6 in particular remain deferred, and no rule, condition, or lifecycle state was added for either.

## Resolution Notes

Questions removed from the list above, with the decision that resolved each one.

### Does a QA defect need an explicit in-scope marker?

Status: Resolved 2026-08-25. Amended 2026-08-29.

Resolved by: [ADR-003](../adr/ADR-003.md) 3.11, amended 2026-08-29 by [ADR-004](../adr/ADR-004.md) 4.14.

Amendment: as originally recorded, ADR-003 3.11 classified a different-Feature association both as unresolved scope and as non-blocking out-of-scope work. The Builder resolved the contradiction in favour of out-of-scope: a defect resolving to a different Feature does not block the Feature being accepted. Only genuinely unresolved scope blocks. The underlying answer below is unchanged.

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
