# Current Focus

**Set 2026-09-05.** Update whenever the focus changes. If this looks stale, trust
[Project-State](Project-State.md) and the git log over this page.

## The One Next Action

**Establish the Checkpoint 7 decisions as ADR-008, before any API code exists.**

Checkpoints 1 through 6 are delivered and green. **The OS enforces.** A transition
whose conditions are not met is refused, the entity is left untouched, and the
refusal is recorded durably in the same committed transaction that discovered it.

Checkpoint 7 is the FastAPI control plane — the first layer that exposes any of
this to the outside world. It is **not blocked**, but the established rhythm says
the ADR comes first, and there are real questions to settle before writing routes.

## What Checkpoint 7 Has To Decide

Not yet ruled on. These are the ones the record already points at:

- **How a rejection becomes an HTTP response.** [Blueprint §7.2](../docs/02-implementation/Implementation-Blueprint.md)
  names `422 Unprocessable Entity` with the structured reasons.
  [ADR-005](../adr/ADR-005.md) 5.12 is explicit that `NotFoundError`,
  `ConcurrencyConflictError` and `PersistenceError` **carry no HTTP status codes**
  and that the transport mapping belongs here.
- **Who the requesting Actor is, and how the API knows.** Every Kernel operation
  takes an initiator. Authentication is not designed anywhere.
- **What the API exposes of the event stream**, which is what
  [the UI](../ui/README.md) is waiting for.
- **Whether the per-event-type payload schemas are settled here.**
  [ADR-006](../adr/ADR-006.md) 6.5 deferred them for want of a consumer;
  Checkpoint 6 wrote a deliberately minimal payload rather than guessing.

## What Checkpoint 6 Delivered

| Ruling | Landed as |
| :--- | :--- |
| [7.1](../adr/ADR-007.md#71-an-implementation-task-is-any-task-whose-capability-is-not-qa) | `ImplementationTasksAcceptedRule` |
| [7.2](../adr/ADR-007.md#72-code-tests-and-reasoning-are-the-feature-level-evidence-set) | `FeatureEvidenceRequiredRule` |
| [7.3](../adr/ADR-007.md#73-reviewers-are-routed-by-capability-and-may-never-review-their-own-work) | `Task.reviewer_id`, `core/routing.py`, `ReviewerAssignedRule` |
| [7.4](../adr/ADR-007.md#74-qa-rounds-select-the-current-defect-position) | `Feature.qa_round`, `QAReport.qa_round`, the shared round selector |
| [7.5](../adr/ADR-007.md#75-tasks_instantiated-is-discharged-by-machinery-not-by-ruling) | `OSKernel.activate_plan` |

Plus the twelve rules the vertical slice walks that Checkpoint 3 deferred by scope,
and `core/` itself: the Kernel, the Validation-First transition runner, the context
loader, and reviewer routing. **The Rule Coverage Gate passes.**

## The Checks That Are Not Optional — Now Written

Each of these exists because something is **not enforced by construction**. They
are the tests to keep, not to tidy away:

- The emit sits beside the append it announces, and `core/runner.py` is the only
  caller of the emitter ([ADR-006](../adr/ADR-006.md) 6.9) —
  `tests/unit/test_rule_invariants.py`.
- `qa_round` advances on the rework loop and on no other transition
  ([ADR-007](../adr/ADR-007.md) 7.4) — `tests/integration/test_kernel_adr_007.py`.
- A QA Report is stamped from the Feature's current round at recording time.
- A Worker is never routed their own Task, including through a Revision they
  authored ([ADR-007](../adr/ADR-007.md) 7.3).
- An empty eligible-Reviewer set refuses with a reason naming the cause.
- A refused transition leaves the entity untouched and a durable record behind
  ([Blueprint §7.2](../docs/02-implementation/Implementation-Blueprint.md)) —
  `tests/integration/test_kernel_transitions.py`.

## The Established Working Rhythm

Every checkpoint has landed as **two commits**, in this order:

1. `docs: establish Checkpoint N <topic> decisions` — the ADR first.
2. `feat: implement Checkpoint N <topic>` — exactly what the ADR authorised.

An amendment gets its own docs commit if implementation surfaces something the ADR
did not foresee — [ADR-006](../adr/ADR-006.md) 6.11 is the worked example.

## Not The Focus

**The UI is finished for now** and parked at the Builder's instruction
([ui/](../ui/README.md)). Checkpoint 6 now writes real events; the UI still cannot
consume them until Checkpoint 7 exposes them. Revisit when the Builder raises it.

**The five remaining `PENDING_RULE_EXPANSION` conditions.** Every one governs a
rework or branch edge the Foundation v1 vertical slice does not walk, so none
blocks anything. They are a recorded scope decision, not a debt to clear now.

## Definition Of Done For Checkpoint 7

`pytest`, `ruff check`, `ruff format --check` and `mypy src` all green; the
Checkpoint 7 endpoints exercised by integration tests; and
[Project-State](Project-State.md) updated the same day.
