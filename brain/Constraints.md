# Constraints

## Purpose

The boundaries this project works inside. Breaking one of these is not a trade-off
to weigh — it is a decision to escalate.

## Architectural

| Constraint | Source |
| :--- | :--- |
| Work is never completed by the agent that performs it | [ADR-001](../adr/ADR-001.md) |
| Only independently generated `SYSTEM` evidence satisfies an evidence requirement | Design Session 005, ADR-001 |
| Conditions are evaluated **before** any mutation; a refusal still commits its record | Blueprint §7.2 |
| Only the Kernel mutates state, records audit and publishes events | [ADR-004](../adr/ADR-004.md) 4.7 |
| Rules are pure, read-only, and never load their own facts | [ADR-004](../adr/ADR-004.md) 4.4, 4.6 |
| An undefined standard fails closed, never as "nothing required" | [ADR-004](../adr/ADR-004.md) 4.9 |
| The Kernel may not go live while a required condition is unenforced | [ADR-004](../adr/ADR-004.md) 4.12 |

## Layering

`domain` depends on nothing beyond Pydantic and the standard library. `state` and
`rules` depend only on `domain`, and **`rules` must not import `state`** — both
consume the condition vocabulary `domain` owns. `storage` must not import `rules`.
`events` depends on `domain` and `storage`, never the reverse. `ui/` imports
nothing and is imported by nothing.

Pinned by `tests/unit/test_domain_isolation.py` and `test_storage_boundaries.py`.

## Persistence

- History is additive. Append-only rows are inserted, never updated.
- **No generic delete exists anywhere.** Foreign keys `RESTRICT`; no cascade.
- Append-only tables carry no optimistic-lock version column.
- Repositories return domain objects only; an ORM row never crosses the boundary.
- Repositories never commit — the transaction owner decides.
- Applied migrations are never edited.
- Persistence metadata timestamps are **never** used for ordering, filtering or
  authoritative QA-result selection ([ADR-005](../adr/ADR-005.md) 5.9).

## Events

- PostgreSQL is the durable store; `LISTEN/NOTIFY` is only a wake-up.
- `sequence_number` is the sole ordering authority, and is **not** a QA-result selector.
- The event type vocabulary is closed at thirteen.
- A notification payload is a thin envelope, never a domain object.

## Recorded limitations — honest, not guarantees

- Append-only is enforced **by construction**, not by database trigger. Code holding
  a raw session could still bypass it.
- A subscriber's position is held in memory. No event is lost, but events appended
  while a subscriber process was down are not replayed to it.
- Staging an event and emitting its notification are two separate calls. Nothing
  structurally prevents doing one without the other — a required check at Checkpoint 6.

## Process

- The ADR is written before the code it governs.
- No lifecycle state, rule, condition, role or vocabulary entry is invented to
  unblock an implementation.
- Deferred capabilities **D-1** through **D-6** remain deferred and unimplemented.
- Superseded records are amended in place with a dated amendment, never rewritten.
