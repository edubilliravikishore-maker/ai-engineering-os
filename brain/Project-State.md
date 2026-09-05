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
| `pytest` | 685 passed |
| `ruff check` | All checks passed |
| `mypy src` | No issues in 88 source files |
| Alembic migrations | 9 applied: `0001_baseline` → `0009_reviewer_and_qa_round` (round-trip verified) |
| Source size | ~9,800 LOC under `src/ai_engineering_os/` |

## Checkpoint Progress — Foundation v1

Checkpoint definitions live in [Implementation-Blueprint §15](../docs/02-implementation/Implementation-Blueprint.md).

| # | Checkpoint | Status | Landed by |
|---|---|---|---|
| 1 | Project Scaffolding & Tooling | **Done** | `774e310` |
| 2 | Pure Domain Entities & State Machines | **Done** | `8fc18bb` |
| 3 | Rule & Policy Engine | **Done** | `5cff96b` |
| 4 | Persistence & Storage Layer | **Done** | `c63db8a` |
| 5 | Event Store & LISTEN/NOTIFY Bus | **Done** | see git log |
| 6 | OS Kernel & Transactional Transition Runner | **Done** | see git log |
| 7 | FastAPI Control Plane & Endpoints | **NEXT — not started** | — |
| 8 | Typed Client SDK & E2E Vertical Slice | Not started | — |

## What Exists In Code

| Package | Delivered at | Contents |
|---|---|---|
| `domain/` | CP2, CP5, CP6 | Immutable entities: Actor, Feature, Plan, Task, WorkPackage, Evidence, QA, Decision; identifiers, enums, errors, conditions; the event vocabulary (ADR-006 6.11); `Task.reviewer_id`, `Feature.qa_round`, `QAReport.qa_round` (ADR-007) |
| `state/` | CP2 | Feature / Plan / Task / WorkPackage state machines over a shared `machine.py` |
| `rules/` | CP3, CP6 | Rule engine, registry, `RuleContext`; **21 rules** across authority, planning, submission, evidence, verification and acceptance; the shared round and revision selectors |
| `storage/` | CP4, CP5 | SQLAlchemy models, mappers, per-aggregate repositories, `unit_of_work.py`, `database.py`; plus `os_events` and `state_transitions_audit` |
| `events/` | CP5 | Notification envelope and single channel, in-transaction `pg_notify` emitter, drain-then-listen subscriber |
| `core/` | CP6 | `kernel.py`, `runner.py` (Validation-First transaction), `context_loader.py`, `routing.py` — **the only layer that mutates, audits and publishes** |
| `api/` | CP7 | Does not exist yet |
| `ui/` | — | **Accepted prototype, parked.** Self-contained, imports nothing, reads nothing yet. See [ui/README.md](../ui/README.md) |

## The Checkpoint 6 Gate — Closed

The Foundation v1 Rule Coverage Gate ([ADR-004 4.12, 4.13](../adr/ADR-004.md))
forbade the Kernel operating while any required transition condition was
unenforced. It was **designed to fail from the end of Checkpoint 3**, and it did:
8 of the 24 required conditions were covered.

**Checkpoint 6 closed it.** Of the 24:

| | Count | |
|---|---|---|
| Enforced by a registered rule | 21 | 6 from CP3, 15 written at CP6 |
| Guaranteed by a domain invariant | 2 | a rule for these could never fail |
| Performed by the Transition Runner | 1 | `TASKS_INSTANTIATED` ([ADR-007 7.5](../adr/ADR-007.md#75-tasks_instantiated-is-discharged-by-machinery-not-by-ruling)) |

`TASKS_INSTANTIATED` is named explicitly rather than counted as covered. Plan
activation *performs* the instantiation, so the runner asserts an outcome it has
just produced inside the same transaction. A gate that quietly rounded that up
would be a gate that could round anything up.

Five conditions remain in `PENDING_RULE_EXPANSION`. **None is Foundation v1
required**: every one governs a rework or branch edge the approved vertical slice
does not walk. They are a scope decision, still recorded, still unenforced.

## Known Limitations — Recorded, Not Overclaimed

Four properties are recorded as limitations rather than claimed as guarantees. None is a defect,
and two of them are risks that Checkpoint 6 **contained by test** rather than removed — the
distinction is deliberate, because claiming otherwise would be claiming a guarantee the code does
not provide:

1. **A subscriber's position is held in memory** (6.6). No event is lost — `os_events` is durable
   and append-only — but events appended while a subscriber process was entirely down are not
   replayed to it on restart.
2. **Staging an event does not itself emit its notification** (6.9). They are two calls, so a
   caller could do the first and omit the second. **Checked, not fixed:** the append and the emit
   sit together in `core/runner.py` and `test_rule_invariants.py` asserts that module is the only
   caller of the emitter. The risk is contained to one place rather than eliminated.
3. **`qa_round` correctness rests on a single Kernel increment** ([ADR-007](../adr/ADR-007.md) 7.4).
   The round advances on exactly one transition — the Feature rework loop — and that is **not
   enforced by construction**. Same class of risk as 6.9, given the same treatment: the increment
   and the status change are one call on the Feature (`opening_next_qa_round`), and
   `test_kernel_adr_007.py` asserts no other transition moves it.
4. **Reviewer routing is deterministic, not fair** ([ADR-007](../adr/ADR-007.md) 7.3). With several
   eligible Reviewers the lowest identifier receives everything. Harmless while the eligible set
   has one member; owed the moment it does not.

A fifth, inherited from ADR-005 5.8: append-only is enforced **by construction** — no repository
exposes an update path — not by database trigger. Code holding a raw session could still bypass it.

## The UI

Settled 2026-09-04 and **parked at the Builder's instruction.** A 3D office built in
pure CSS 3D — [ui/](../ui/README.md), with every decision and trade-off recorded in
[ui/DESIGN-DECISIONS.md](../ui/DESIGN-DECISIONS.md) and the rejected directions kept
in [ui/explorations/](../ui/explorations/README.md).

Checkpoint 6 now writes real events. The UI still cannot go live until Checkpoint 7
exposes them. [ADR-006](../adr/ADR-006.md) 6.5 deferred the per-event-type payload
schemas because no consumer existed, and this is that consumer; Checkpoint 6 wrote a
minimal, deliberately unschematised payload rather than guessing one.

## Related

- [Current-Focus](Current-Focus.md) — the one next action
- [Decision-Index](Decision-Index.md) — where each ruling lives
- [Open-Questions](Open-Questions.md) — what is still undecided
