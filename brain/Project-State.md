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
| `pytest` | 581 passed |
| `ruff check` | All checks passed |
| `mypy src` | No issues in 70 source files |
| Alembic migrations | 7 applied: `0001_baseline` → `0007_decisions` |
| Source size | ~6,500 LOC under `src/ai_engineering_os/` |

## Checkpoint Progress — Foundation v1

Checkpoint definitions live in [Implementation-Blueprint §15](../docs/02-implementation/Implementation-Blueprint.md).

| # | Checkpoint | Status | Landed by |
|---|---|---|---|
| 1 | Project Scaffolding & Tooling | **Done** | `774e310` |
| 2 | Pure Domain Entities & State Machines | **Done** | `8fc18bb` |
| 3 | Rule & Policy Engine | **Done** | `5cff96b` |
| 4 | Persistence & Storage Layer | **Done** | `c63db8a` |
| 5 | Event Store & LISTEN/NOTIFY Bus | **In progress** — [ADR-006](../adr/ADR-006.md) accepted; code not written | — |
| 6 | OS Kernel & Transactional Transition Runner | Not started | — |
| 7 | FastAPI Control Plane & Endpoints | Not started | — |
| 8 | Typed Client SDK & E2E Vertical Slice | Not started | — |

## What Exists In Code

| Package | Delivered at | Contents |
|---|---|---|
| `domain/` | CP2 | Immutable entities: Actor, Feature, Plan, Task, WorkPackage, Evidence, QA, Decision; identifiers, enums, errors, conditions |
| `state/` | CP2 | Feature / Plan / Task / WorkPackage state machines over a shared `machine.py` |
| `rules/` | CP3 | Rule engine, registry, `RuleContext`, evidence / authority / acceptance / dependency rules, result + code types |
| `storage/` | CP4 | SQLAlchemy models, mappers, per-aggregate repositories, `unit_of_work.py`, `database.py` |
| `events/` | CP5 | **Does not exist yet** — this is the next thing to build |
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

Checkpoint 5 does **not** touch the gate, so it can proceed now.

## Related

- [Current-Focus](Current-Focus.md) — the one next action
- [Decision-Index](Decision-Index.md) — where each ruling lives
- [Open-Questions](Open-Questions.md) — what is still undecided
