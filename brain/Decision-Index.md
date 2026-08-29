# Decision Index

## Purpose

Index project decisions when they are recorded.

## Suggested Sections

<!-- Placeholder -->

## Decisions

- [ADR-001: Work Is Never Completed By The Agent That Performs It](../adr/ADR-001.md) — amended 2026-08-25: the independent-verification principle stands; the original illustrative linear workflow is formally superseded.
- [ADR-002: Implementation Foundation & Technology Stack](../adr/ADR-002.md)
- [ADR-003: Foundation v1 Domain Model & Lifecycle Clarifications](../adr/ADR-003.md) — 3.1 to 3.10 record the Checkpoint 2 clarifications; 3.11 to 3.14 record the Builder rulings of 2026-08-25.
  - [3.11 QA Defect Scope](../adr/ADR-003.md#311-qa-defect-scope--verified-structural-association-never-a-declared-boolean) — defect scope is a verified structural association derived by the OS, never a declared boolean.
  - [3.12 Task Creation Timing vs Execution Authorization](../adr/ADR-003.md#312-task-creation-timing-vs-execution-authorization) — Tasks may be created from a DRAFT plan; execution authority derives from plan activation.
  - [3.13 Post-Supersession Routing](../adr/ADR-003.md#313-post-supersession-routing--explicit-coordinator-disposition-no-automatic-migration) — no automatic migration, deletion, or halting; the Coordinator dispositions each unfinished Task explicitly.
  - [3.14 ADR-001 Formal Amendment](../adr/ADR-003.md#314-adr-001-formal-amendment-performed) — authorises the ADR-001 amendment as a formal clarification, not a new architecture.
- [ADR-004: Rule Engine Foundation & Checkpoint 3 Scope](../adr/ADR-004.md) — **Accepted — 2026-08-25.** Records the Rule & Policy Engine architecture and the scope of Checkpoint 3. Supersedes nothing.
  - [4.1 Generic Rule Engine](../adr/ADR-004.md#41-generic-rule-engine-with-explicit-strongly-typed-python-rules) — a reusable engine with explicit strongly typed Python rules; no DSL, no expression language, no LLM evaluation.
  - [4.2 Hybrid Evaluation](../adr/ADR-004.md#42-hybrid-evaluation) — independent failures aggregate; only rules with a declared, failed prerequisite are skipped.
  - [4.3 Deterministic Ordering](../adr/ADR-004.md#43-deterministic-os-owned-rule-ordering) — a fixed OS-owned stage order; agents and runtime configuration never reorder rules.
  - [4.7 Condition Vocabulary Moves To Domain](../adr/ADR-004.md#47-the-condition-vocabulary-moves-to-the-domain-layer) — `domain` owns the vocabulary; `state` declares, `rules` evaluates; `rules` must not depend on `state`.
  - [4.8 Full Phase 0 Revisit](../adr/ADR-004.md#48-checkpoint-2-revisit-performed-in-full-at-checkpoint-3-start) — QA defect scope fields, required Task plan linkage, and the `ORIGINATING_PLAN_ACTIVE` declaration; that rule itself stays deferred.
  - [4.9 Evidence Standards Fail Closed](../adr/ADR-004.md#49-evidence-standards--undefined-capabilities-fail-closed) — no standard is invented for FRONTEND or QA; an undefined standard fails closed, never as "no evidence required". `DB_VERIFICATION` is not mandatory.
  - [4.10 Six Representative CP3 Rules](../adr/ADR-004.md#410-checkpoint-3-rule-scope--six-representative-rules) — the engine is proven against six real rules before the rule library is expanded.
  - [4.11 Four-Way Condition Classification](../adr/ADR-004.md#411-rule-expansion-boundary--four-way-condition-classification) — implemented, PENDING_RULE_EXPANSION, SATISFIED_BY_DOMAIN_INVARIANT, and BLOCKED_CONDITIONS partition the vocabulary.
  - [4.12 Checkpoint 6 Safety Gate](../adr/ADR-004.md#412-checkpoint-6-safety-gate) — the Kernel may not operate while a required Foundation v1 condition is unenforced.
  - [4.13 Required Conditions Derived From The Vertical Slice](../adr/ADR-004.md#413-foundation-v1-required-conditions-derived-from-the-vertical-slice) — the required set is derived from the approved vertical slice, never authored as a separate checklist.

## Placeholders

<!-- Placeholder -->
