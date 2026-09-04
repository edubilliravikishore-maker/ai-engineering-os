# Project State

**Last verified: 2026-09-04** (re-run the Health Check below to refresh this date)

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
| 6 | OS Kernel & Transactional Transition Runner | **NEXT — blocked, see below** | — |
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

## Known Blocker Ahead — Do Not Walk Into This Blind

Checkpoint 6 has a **blocking precondition**: the Foundation v1 Rule Coverage Gate
([ADR-004 4.12, 4.13](../adr/ADR-004.md)). Of the 24 required transition conditions,
**6 are implemented, 2 are satisfied by domain invariant, and 16 are outstanding**
(12 in `PENDING_RULE_EXPANSION`, 4 in `BLOCKED_CONDITIONS`).

The gate is *designed* to fail at the end of Checkpoint 3 — that is expected, not a defect.
But the four `BLOCKED_CONDITIONS` depend on three unresolved Builder questions
(Blueprint §14 items 15, 16, 17: the definition of "implementation task", the Feature-level
mandatory evidence set, and the Reviewer assignment model). **These are on the critical path
to Checkpoint 6 and cannot be decided silently during implementation.**

Checkpoint 5 did **not** touch the gate. **Checkpoint 6 does, and cannot start until those three
questions are answered.** They are architecture decisions, not implementation details.

## Known Limitations — Recorded, Not Overclaimed

Two properties are recorded as limitations rather than claimed as guarantees. Both are written
into [ADR-006](../adr/ADR-006.md) and neither is a defect:

1. **A subscriber's position is held in memory** (6.6). No event is lost — `os_events` is durable
   and append-only — but events appended while a subscriber process was entirely down are not
   replayed to it on restart.
2. **Staging an event does not itself emit its notification** (6.9). They are two calls, so a
   future caller could do the first and omit the second. The component that would omit it is the
   Checkpoint 6 Kernel, which does not exist yet. **This is a required check at Checkpoint 6.**

A third, inherited from ADR-005 5.8: append-only is enforced **by construction** — no repository
exposes an update path — not by database trigger. Code holding a raw session could still bypass it.

## Related

- [Current-Focus](Current-Focus.md) — the one next action
- [Decision-Index](Decision-Index.md) — where each ruling lives
- [Open-Questions](Open-Questions.md) — what is still undecided
