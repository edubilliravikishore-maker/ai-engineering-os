# Current Focus

**Set 2026-09-04.** Update whenever the focus changes. If this looks stale, trust
[Project-State](Project-State.md) and the git log over this page.

## The One Next Action

**Answer the four Builder questions that block Checkpoint 6, and record them as
ADR-007.** Not code.

Checkpoints 1 through 5 are delivered, green and pushed. Checkpoint 6 is next in
sequence and **it is blocked** — not by missing code, but by four architecture
decisions only the Builder can make.

## The Four Questions

The Foundation v1 Rule Coverage Gate ([ADR-004](../adr/ADR-004.md) 4.12, 4.13)
forbids the Kernel becoming operational while any required transition condition is
unenforced. Four `BLOCKED_CONDITIONS` wait on these
([Blueprint §14](../docs/02-implementation/Implementation-Blueprint.md)):

| Item | Question |
| :--- | :--- |
| 15 | What is the definition of an "implementation task"? |
| 16 | What is the Feature-level mandatory evidence set? |
| 17 | What is the Reviewer assignment and routing model? |
| 18 | Which QA report states a Feature's current defect position? |

**Item 18 has had both easy answers deliberately closed off.** ADR-005 5.9 forbids
using the persistence metadata timestamps; ADR-006 6.1 confirms `sequence_number`
is an append-order key and not a QA-result selector. Whatever is chosen has to be
designed, which is the point.

## Why Not Just Start Coding

Because the gate exists to stop exactly that. Deciding any of these silently inside
an implementation is the failure mode ADR-003 and ADR-004 were written to prevent,
and the project has now recorded four separate times that they must not be settled
in passing.

## The Established Working Rhythm

Every checkpoint has landed as **two commits**, in this order:

1. `docs: establish Checkpoint N <topic> decisions` — the ADR first, resolving
   ambiguity before any code exists.
2. `feat: implement Checkpoint N <topic>` — exactly what the ADR authorised.

An amendment gets its own docs commit when implementation surfaces something the
ADR did not foresee — [ADR-006](../adr/ADR-006.md) 6.11 is the worked example.

So Checkpoint 6 starts with **ADR-007**, recording the four rulings above.

## Carried Into Checkpoint 6

Three things Checkpoint 5 deliberately left for the Kernel:

- **The Kernel must call the notification emitter itself** ([ADR-006](../adr/ADR-006.md) 6.9).
  Staging an event and emitting its wake-up are two separate calls and this is
  **not enforced by construction**. Verifying the Kernel never does one without the
  other is a required check.
- **Per-event-type payload schemas** ([ADR-006](../adr/ADR-006.md) 6.5) were deferred
  because no consumer existed. [The UI](../ui/README.md) is now that consumer.
- **The authoritative QA-result mechanism** — item 18 above.

## Not The Focus

**The UI is finished for now** and parked at the Builder's instruction
([ui/](../ui/README.md)). Revisit only when the Builder raises it, or when
Checkpoint 7 can feed it real events.

## Definition Of Done For Checkpoint 6

`pytest`, `ruff check`, `ruff format --check` and `mypy src` all green; the Rule
Coverage Gate passing rather than expected-to-fail; and
[Project-State](Project-State.md) updated the same day.
