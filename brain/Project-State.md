# Project State

**Last verified: 2026-09-05** (re-run the Health Check below to refresh this date)

## Purpose

The single page that answers "where is this project right now?" without reading the Blueprint.

## Health Check

Run these three commands. All three are green as of the date above.

```bash
.venv/bin/python -m pytest -q && .venv/bin/ruff check . && .venv/bin/mypy src
```

| Check | Result |
|---|---|
| `pytest` | 606 passed |
| `ruff check` | All checks passed |
| `mypy src` | No issues in 79 source files |
| Alembic migrations | 8 applied: `0001_baseline` → `0008_events_and_transition_audit` (round-trip verified) |
| Source size | ~7,400 LOC under `src/ai_engineering_os/` |

## Checkpoint Progress — Foundation v1

Checkpoint definitions live in [Implementation-Blueprint §15](../docs/02-implementation/Implementation-Blueprint.md).

| # | Checkpoint | Status | Landed by |
|---|---|---|---|
| 1 | Project Scaffolding & Tooling | **Done** | `774e310` |
| 2 | Pure Domain Entities & State Machines | **Done** | `8fc18bb` |
| 3 | Rule & Policy Engine | **Done** | `5cff96b` |
| 4 | Persistence & Storage Layer | **Done** | `c63db8a` |
| 5 | Event Store & LISTEN/NOTIFY Bus | **Done** | see git log |
| 6 | OS Kernel & Transactional Transition Runner | **NEXT — unblocked by [ADR-007](../adr/ADR-007.md), not started** | — |
| 7 | FastAPI Control Plane & Endpoints | Not started | — |
| 8 | Typed Client SDK & E2E Vertical Slice | Not started | — |

## What Exists In Code

| Package | Delivered at | Contents |
|---|---|---|
| `domain/` | CP2, CP5 | Immutable entities: Actor, Feature, Plan, Task, WorkPackage, Evidence, QA, Decision; identifiers, enums, errors, conditions; plus the event vocabulary (ADR-006 6.11) |
| `state/` | CP2 | Feature / Plan / Task / WorkPackage state machines over a shared `machine.py` |
| `rules/` | CP3 | Rule engine, registry, `RuleContext`, evidence / authority / acceptance / dependency rules, result + code types |
| `storage/` | CP4, CP5 | SQLAlchemy models, mappers, per-aggregate repositories, `unit_of_work.py`, `database.py`; plus `os_events` and `state_transitions_audit` |
| `events/` | CP5 | Notification envelope and single channel, in-transaction `pg_notify` emitter, drain-then-listen subscriber |
| `core/` | CP6 | Does not exist yet (Kernel, TransitionRunner) |
| `api/` | CP7 | Does not exist yet |
| `ui/` | — | **Accepted prototype, parked.** Self-contained, imports nothing, reads nothing yet. See [ui/README.md](../ui/README.md) |

## The Checkpoint 6 Gate — Where It Stands

Checkpoint 6 has a **blocking precondition**: the Foundation v1 Rule Coverage Gate
([ADR-004 4.12, 4.13](../adr/ADR-004.md)). Of the 24 required transition conditions,
**6 are implemented, 2 are satisfied by domain invariant, and 16 are outstanding**
(12 in `PENDING_RULE_EXPANSION`, 4 in `BLOCKED_CONDITIONS`).

The gate is *designed* to fail at the end of Checkpoint 3 — that is expected, not a defect.
Checkpoint 5 did not touch it. **Checkpoint 6 is the checkpoint that closes it.**

**The three Builder questions that blocked it were answered on 2026-09-05** and recorded
as [ADR-007](../adr/ADR-007.md) — the definition of "implementation task" (7.1), the
Feature-level mandatory evidence set (7.2), and the Reviewer assignment model (7.3).
A fourth ruling (7.4) closed the authoritative-QA-result question that had left
`QAInScopeZeroDefectsRule` performing no selection at all.

**The decisions exist; the code does not.** The three conditions stay in
`BLOCKED_CONDITIONS` until Checkpoint 6 writes their rules, and the fourth entry,
`TASKS_INSTANTIATED`, leaves that set when the Transition Runner exists
([ADR-007 7.5](../adr/ADR-007.md#75-tasks_instantiated-is-discharged-by-machinery-not-by-ruling)).
Nothing in the gate arithmetic above has moved yet.

## Known Limitations — Recorded, Not Overclaimed

Three properties are recorded as limitations rather than claimed as guarantees. None is a defect:

1. **A subscriber's position is held in memory** (6.6). No event is lost — `os_events` is durable
   and append-only — but events appended while a subscriber process was entirely down are not
   replayed to it on restart.
2. **Staging an event does not itself emit its notification** (6.9). They are two calls, so a
   future caller could do the first and omit the second. The component that would omit it is the
   Checkpoint 6 Kernel, which does not exist yet. **This is a required check at Checkpoint 6.**
3. **`qa_round` correctness rests on a single Kernel increment** ([ADR-007](../adr/ADR-007.md) 7.4).
   The round is incremented on exactly one transition — the Feature rework loop — and that is
   **not enforced by construction**. Same class of risk as 6.9 above, and it needs the same
   treatment: an explicit Checkpoint 6 test that the rework loop increments and nothing else does.

A fourth, inherited from ADR-005 5.8: append-only is enforced **by construction** — no repository
exposes an update path — not by database trigger. Code holding a raw session could still bypass it.

## The UI

Settled 2026-09-04 and **parked at the Builder's instruction.** A 3D office built in
pure CSS 3D — [ui/](../ui/README.md), with every decision and trade-off recorded in
[ui/DESIGN-DECISIONS.md](../ui/DESIGN-DECISIONS.md) and the rejected directions kept
in [ui/explorations/](../ui/explorations/README.md).

It cannot go live until Checkpoints 6 and 7 exist to feed it. It is still useful
before then: [ADR-006](../adr/ADR-006.md) 6.5 deferred the per-event-type payload
schemas because no consumer existed, and this is that consumer.

## Related

- [Current-Focus](Current-Focus.md) — the one next action
- [Decision-Index](Decision-Index.md) — where each ruling lives
- [Open-Questions](Open-Questions.md) — what is still undecided
