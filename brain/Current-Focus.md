# Current Focus

**Set 2026-09-05.** Update whenever the focus changes. If this looks stale, trust
[Project-State](Project-State.md) and the git log over this page.

## The One Next Action

**Implement Checkpoint 6 — the OS Kernel and the transactional Transition Runner,
exactly as [ADR-007](../adr/ADR-007.md) authorises.**

The four Builder questions that blocked this checkpoint were answered on
2026-09-05 and recorded as ADR-007. **Checkpoint 6 is no longer blocked.**

## What ADR-007 Ruled

| # | Question | Ruling |
| :--- | :--- | :--- |
| 15 | What is an "implementation task"? | Any Task whose capability is **not** QA ([7.1](../adr/ADR-007.md#71-an-implementation-task-is-any-task-whose-capability-is-not-qa)) |
| 16 | Feature-level mandatory evidence? | `GIT_DIFF` + `TEST_OUTPUT` + `REASONING` ([7.2](../adr/ADR-007.md#72-code-tests-and-reasoning-are-the-feature-level-evidence-set)) |
| 17 | Reviewer assignment and routing? | Route by capability, never self-review ([7.3](../adr/ADR-007.md#73-reviewers-are-routed-by-capability-and-may-never-review-their-own-work)) |
| 18 | Which QA report is current? | The current **QA round**'s reports ([7.4](../adr/ADR-007.md#74-qa-rounds-select-the-current-defect-position)) |

`TASKS_INSTANTIATED` — the fourth `BLOCKED_CONDITIONS` entry — needed no ruling.
It is discharged by the runner itself ([7.5](../adr/ADR-007.md#75-tasks_instantiated-is-discharged-by-machinery-not-by-ruling)).

## What Checkpoint 6 Has To Build

Read [ADR-007 *Implementation impact*](../adr/ADR-007.md#implementation-impact)
for the full table. In outline:

- **Domain:** `Task.reviewer_id`, `Feature.qa_round`, `QAReport.qa_round`, and the
  `Actor` capability validator extended to `REVIEWER`.
- **Storage:** migration `0009` for the three new columns.
- **Rules:** three new rules; a round filter on `QAInScopeZeroDefectsRule` and
  `QAFinalPassRecordedRule`; three conditions moved out of `BLOCKED_CONDITIONS`.
- **`core/`:** the Kernel, the Transition Runner, reviewer routing, and QA round
  management.

## The Checks That Are Not Optional

Every one of these exists because something is **not enforced by construction**:

- The Kernel calls the notification emitter itself ([ADR-006](../adr/ADR-006.md) 6.9).
  Staging an event and emitting its wake-up are two separate calls.
- `qa_round` is incremented on the rework loop and on **no other transition**
  ([ADR-007](../adr/ADR-007.md) 7.4).
- A QA Report is stamped from the Feature's current round at recording time.
- A Worker can never be routed their own Task for review, including through a
  Revision they authored ([ADR-007](../adr/ADR-007.md) 7.3).
- An empty eligible-Reviewer set refuses the transition, with a reason naming the
  cause.

## The Established Working Rhythm

Every checkpoint has landed as **two commits**, in this order:

1. `docs: establish Checkpoint N <topic> decisions` — the ADR first.
2. `feat: implement Checkpoint N <topic>` — exactly what the ADR authorised.

ADR-007 is the first of that pair for Checkpoint 6. An amendment gets its own docs
commit if implementation surfaces something the ADR did not foresee —
[ADR-006](../adr/ADR-006.md) 6.11 is the worked example.

## Not The Focus

**The UI is finished for now** and parked at the Builder's instruction
([ui/](../ui/README.md)). Revisit only when the Builder raises it, or when
Checkpoint 7 can feed it real events.

## Definition Of Done For Checkpoint 6

`pytest`, `ruff check`, `ruff format --check` and `mypy src` all green; the Rule
Coverage Gate **passing** rather than expected-to-fail; and
[Project-State](Project-State.md) updated the same day.
