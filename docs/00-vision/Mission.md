# Mission

> **DRAFT — 2026-09-04.** Written from the Implementation Blueprint and the ADRs.
> **The Builder has not yet ruled on this wording.** Correct it freely.

## Mission Statement

**Build Foundation v1: an OS that can carry one Feature from creation to
acceptance, refusing every transition whose conditions are not met and recording
why.**

One Feature, one plan, a handful of Tasks, walked end to end by the Checkpoint 8
vertical slice. Narrow on purpose — the point is that the enforcement is real, not
that the system is broad.

## Scope

**In scope for Foundation v1**

- The domain model and lifecycle state machines for Feature, Plan, Task and Work Package.
- A deterministic Rule Engine, with rules proven against real conditions rather than examples.
- PostgreSQL persistence: authoritative state, append-only history, no path that rewrites history.
- An append-only event store and a `LISTEN/NOTIFY` wake-up.
- A Kernel that evaluates before it mutates, and records refusals durably.
- An HTTP control plane and a typed client.
- A vertical slice test proving all of it holds together.

**Explicitly out of scope**

- Agent runtimes, prompts, model selection, sandboxing.
- The Coordinator lifecycle and Domain Registry (**D-2**, **D-3**).
- Escalation blocking and a `BLOCKED` state (**D-1**).
- Task stop / abandon (**D-6**).
- Production deployment, scaling, distribution.

Each deferral is a recorded ruling, not an omission. None is withdrawn.

## How we know it is done

`pytest`, `ruff` and `mypy` green; every migration reversible; the Rule Coverage
Gate passing rather than expected-to-fail; and the eleven-step vertical slice
running from Feature creation to acceptance.

## The measure that matters most

**A Worker cannot get work accepted by asserting it is done.** If that ever becomes
possible, Foundation v1 has failed regardless of what else passes.
