# Current Focus

**Set 2026-09-04.** Update this file whenever the focus changes. If it is stale, trust
[Project-State](Project-State.md) and the git log over this page.

## The One Next Action

**Checkpoint 5 — Event Store & LISTEN/NOTIFY Bus. Implementation.**

The decisions are recorded: [ADR-006](../adr/ADR-006.md), accepted 2026-09-04, nine
rulings indexed in [Decision-Index](Decision-Index.md). Step 1 of the rhythm below is
**done**; the next action is step 2, the code.

Everything before it is done, green, and committed. Nothing blocks it.

## Why This And Not Something Else

- Checkpoints run in order; 1–4 are done and 5 is the next in the Blueprint sequence.
- Checkpoint 6 (the Kernel) is **blocked** by the Rule Coverage Gate and by three
  undecided Builder questions — see [Project-State](Project-State.md#known-blocker-ahead--do-not-walk-into-this-blind).
- Checkpoint 5 is the last piece of machinery the Kernel needs, and it is unblocked.

## Checkpoint 5 Scope

From [Blueprint §15](../docs/02-implementation/Implementation-Blueprint.md) and
[ADR-005 5.13](../adr/ADR-005.md#513-events-and-transition-audit-deferred-to-checkpoint-5):

**In scope**

1. `os_events` — table, model, migration, append-only repository.
2. `state_transitions_audit` — table, model, migration, repository. Required by the
   §7.2 Validation-First invariant so a *rejected* transition has a durable place to land
   before the Checkpoint 6 runner needs it. **No earlier checkpoint owned this table.**
3. `EventModel` and append-only event recording under `src/ai_engineering_os/events/`.
4. PostgreSQL `LISTEN/NOTIFY` emitter and async subscriber.
   PostgreSQL is the durable store; `LISTEN/NOTIFY` is **only a wake-up mechanism** (ADR-002).
5. Integration tests for event persistence and notification wake-up.

**Out of scope**

- No Kernel, no TransitionRunner, no context loader (Checkpoint 6).
- No HTTP layer (Checkpoint 7).
- No new rule, transition condition, `RuleContext` fact, or lifecycle state.
- No resolution of Blueprint §14 items 15, 16, 17 — those are Builder decisions.

## The Established Working Rhythm

Every checkpoint so far has landed as **two commits**, in this order. Follow it.

1. `docs: establish Checkpoint N <topic> decisions` — write the ADR **first**, resolving
   ambiguity before code exists. (ADR-004 for CP3, ADR-005 for CP4.)
2. `feat: implement Checkpoint N <topic>` — implement exactly what the ADR authorised.

Checkpoint 5's step 1 is **[ADR-006](../adr/ADR-006.md)** — written and accepted. It
supersedes the Blueprint §7.2 step 7 post-commit emit, and amends that section's
transition-audit description and channel name. Those three edits to the Blueprint belong
with the implementation commit, not before it.

## Definition Of Done

`pytest`, `ruff check`, and `mypy src` all green, plus the new integration tests, plus
[Project-State](Project-State.md) updated to mark Checkpoint 5 done.
