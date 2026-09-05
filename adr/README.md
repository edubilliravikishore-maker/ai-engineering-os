# Architecture Decision Records

## Purpose

The authoritative decision trail. An ADR records what was decided, what it
supersedes, and what it explicitly defers — written **before** the code it governs.

One-line summaries of every numbered ruling are in
[brain/Decision-Index.md](../brain/Decision-Index.md). Start there to find a
decision; come here to read it.

## How an ADR works here

Each decision separates three things:

- **Existing architectural requirement** — already true. Not decided here.
- **Clarification** — what this record actually resolves.
- **Explicit deferral** — what will *not* be built, and what remains owed.

Superseded records are **amended in place with a dated amendment**, never rewritten
or deleted. Trade-offs are recorded as trade-offs, and a limitation is never
overclaimed as a guarantee.

## The records

| ADR | Subject | Status |
| :--- | :--- | :--- |
| [ADR-001](ADR-001.md) | Work is never completed by the agent that performs it | Accepted; amended 2026-08-25 |
| [ADR-002](ADR-002.md) | Implementation foundation & technology stack | Accepted |
| [ADR-003](ADR-003.md) | Foundation v1 domain model & lifecycle clarifications | Accepted; §3.11 amended 2026-08-29 |
| [ADR-004](ADR-004.md) | Rule engine foundation & Checkpoint 3 scope | Accepted; §4.14–4.16 added 2026-08-29 |
| [ADR-005](ADR-005.md) | Persistence architecture & Checkpoint 4 scope | Accepted 2026-09-02 |
| [ADR-006](ADR-006.md) | Event layer architecture & Checkpoint 5 scope | Accepted 2026-09-04; §6.11 added same day |
| [ADR-007](ADR-007.md) | The four blocked conditions & Checkpoint 6 preconditions | Accepted 2026-09-05 |

**ADR-008 is the next one**, if Checkpoint 6 implementation surfaces something
ADR-007 did not foresee. See [brain/Current-Focus.md](../brain/Current-Focus.md).

## Template

[ADR-000-template.md](ADR-000-template.md). ADR-005 and ADR-006 are the fullest
worked examples of the house structure.
