# Roadmap

## Purpose

Track the project's evolving roadmap. Checkpoint detail lives in
[Implementation-Blueprint §15](../02-implementation/Implementation-Blueprint.md);
live status lives in [brain/Project-State](../../brain/Project-State.md).
This page is the horizon view only.

## Current Horizon — Foundation v1

Foundation v1 is complete when the Checkpoint 8 vertical slice runs end to end.

```
CP1 Scaffolding      ✅ done
CP2 Domain & State   ✅ done
CP3 Rule Engine      ✅ done
CP4 Persistence      ✅ done
CP5 Event Layer      ◀ next — unblocked
CP6 OS Kernel        ⛔ blocked by the Rule Coverage Gate (ADR-004 4.12/4.13)
CP7 FastAPI          ⏸ after CP6
CP8 Client + E2E     ⏸ after CP7
```

### The Critical Path

The only real risk to Foundation v1 is the **Checkpoint 6 gate**. Four
`BLOCKED_CONDITIONS` cannot be implemented until three Builder questions are answered
(Blueprint §14):

| Item | Question |
|---|---|
| 15 | What is the definition of an "implementation task"? |
| 16 | What is the Feature-level mandatory evidence set? |
| 17 | What is the Reviewer assignment model? |

These are **architecture decisions, not implementation details**, and they must be
recorded in an ADR before Checkpoint 6 code is written. They can be answered in parallel
with Checkpoint 5 — doing so removes the only foreseeable stall in the sequence.

## Future Considerations

Beyond Foundation v1, deferred by explicit ruling rather than oversight:

- **D-1 and D-6** — deferred capabilities recorded by [ADR-003](../../adr/ADR-003.md);
  no generic delete exists that could implement either by accident.
- **Feature supersession consequence** — Blueprint §14 item 9; unresolved, must not be
  decided silently inside Checkpoint 6.
- **Coordinator-initiated disposition** on `ACTIVE -> SUPERSEDED` — persisted record and
  stop state deferred (§14 item 11).
- **The seven non-required transition conditions** — the rework and multi-task edges the
  Foundation v1 slice does not walk. Part of the architecture, not withdrawn, not required
  for the gate.
