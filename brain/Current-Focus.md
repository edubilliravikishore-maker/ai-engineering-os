# Current Focus

**Set 2026-09-04.** Update this file whenever the focus changes. If it is stale, trust
[Project-State](Project-State.md) and the git log over this page.

## The One Next Action

**Answer the three Builder questions that block Checkpoint 6.** Not code.

Checkpoints 1 through 5 are delivered, green, and committed. Checkpoint 6 is the next in
sequence and **it is blocked** — not by missing code, but by three architecture decisions
only the Builder can make.

## What Is Blocking, Precisely

The Foundation v1 Rule Coverage Gate ([ADR-004](../adr/ADR-004.md) 4.12, 4.13) forbids the
Kernel becoming operational while any required transition condition is unenforced. Four
`BLOCKED_CONDITIONS` cannot be implemented until these are ruled on
([Blueprint §14](../docs/02-implementation/Implementation-Blueprint.md)):

| Item | Question |
| :--- | :--- |
| 15 | What is the definition of an "implementation task"? |
| 16 | What is the Feature-level mandatory evidence set? |
| 17 | What is the Reviewer assignment and routing model? |

A fourth is on the same critical path and is **not** one of the four blocked conditions:

| Item | Question |
| :--- | :--- |
| 18 | Which QA report states a Feature's current defect position? ([ADR-004](../adr/ADR-004.md) 4.15) |

ADR-005 5.9 and ADR-006 6.1 both **add prohibitions rather than answers** to item 18: neither
the persistence metadata timestamps nor `sequence_number` may be used to build that selector.
It must be designed before Checkpoint 6.

## Why Not Just Start Coding Checkpoint 6

Because the gate exists to stop exactly that. Deciding any of these silently inside an
implementation is the failure mode ADR-003 and ADR-004 were written to prevent — and the
project has now recorded four separate times that these must not be decided in passing.

## The Established Working Rhythm

Every checkpoint so far has landed as **two commits**, in this order. Follow it.

1. `docs: establish Checkpoint N <topic> decisions` — write the ADR **first**, resolving
   ambiguity before code exists. (ADR-004 for CP3, ADR-005 for CP4, ADR-006 for CP5.)
2. `feat: implement Checkpoint N <topic>` — implement exactly what the ADR authorised.

An amendment gets its own docs commit when implementation surfaces something the ADR did not
foresee — as ADR-006 6.11 did for the event vocabulary placement.

So Checkpoint 6 starts with **ADR-007**, recording the four rulings above.

## Carried Into Checkpoint 6

Two things Checkpoint 5 deliberately left for the Kernel:

- **The emitter is called by the Kernel, not by the repository** ([ADR-006](../adr/ADR-006.md) 6.9).
  Staging an event and emitting its wake-up are two calls and this is **not enforced by
  construction**. Verifying the Kernel never does one without the other is a required check.
- **Per-event-type payload schemas** ([ADR-006](../adr/ADR-006.md) 6.5) were deferred because the
  consumers did not exist. At Checkpoint 6 they start to.

## Definition Of Done For Checkpoint 6

`pytest`, `ruff check`, `ruff format --check`, and `mypy src` all green; the Rule Coverage Gate
passing rather than expected-to-fail; and [Project-State](Project-State.md) updated.
