# Project Context

## Purpose

Everything a new session needs before touching anything. Read this, then
[Project-State](Project-State.md), then [Current-Focus](Current-Focus.md).

## What this project is

**AI Engineering OS** — a deterministic operating layer for multi-agent software
engineering. It does not write code and does not manage agents. It decides whether
a piece of work is allowed to advance, and records why.

The one idea underneath everything ([ADR-001](../adr/ADR-001.md)): **work is never
completed by the agent that performs it.** An agent saying "I tested it" proves
nothing, so the OS requires independently generated evidence and separates who does
the work from who accepts it.

## Where it is

Foundation v1, Checkpoints 1–5 delivered. Checkpoint 6 blocked on four Builder
decisions. See [Project-State](Project-State.md).

## How work happens here

**Documents before code, always.** Each checkpoint lands as two commits: the ADR
recording the decisions, then the implementation of exactly what it authorised.
When implementation surfaces something the ADR missed, that gets its own dated
amendment ([ADR-006](../adr/ADR-006.md) 6.11 is the worked example).

**Decisions belong to the Builder.** Where the architecture has deliberately left a
question open, it must not be answered inside an implementation. Several ADRs say
so explicitly, and the Checkpoint 6 gate exists to enforce it.

**Nothing is invented for convenience.** No lifecycle state, rule, condition, role
or vocabulary entry gets added to make code work. If one seems necessary, stop.

## Non-negotiables

- `domain` depends on nothing but Pydantic and the standard library.
- `rules` must not import `state`; `storage` must not import `rules`.
- Append-only tables have no update method, no delete, no version column.
- No generic delete exists anywhere in the persistence layer.
- Persistence metadata timestamps are never used for ordering or selection.
- Deferred capabilities **D-1** through **D-6** stay deferred; no constraint admits
  their states.

The first three are pinned by tests that fail loudly. The rest are held by
discipline and by review.

## Working with the Builder

Explain in plain language with a concrete worked example. Present one decision at a
time with a recommendation and its honest trade-off, then wait for the ruling. Say
plainly when new evidence weakens something already recommended. Keep the formal
register for the ADRs and the commit messages, not the conversation.

## Known failure mode

**The `brain/` files going stale.** It happened once, through Checkpoint 4, and the
project nearly lost its thread despite the code being perfectly healthy. See
[Lessons-Learned](Lessons-Learned.md). Update [Project-State](Project-State.md) in
the same commit as the work, every time.
