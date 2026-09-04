# System Terminology

## Purpose

Fix the vocabulary of the system, so the same word means the same thing in an ADR,
in the code and in conversation.

Authoritative definitions live in `src/ai_engineering_os/domain/`. This page is the
plain-language index.

## Actors

| Term | Meaning |
| :--- | :--- |
| **Builder** | The human. Final authority. Makes the decisions no agent may make. |
| **Orchestrator** | Highest agent authority. Handles escalations. |
| **Coordinator** | Owns a Feature: plans it, assigns Tasks, accepts the result. |
| **Worker** | Performs the work and submits it with evidence. Never accepts it. |
| **Reviewer** | Reads submitted work. Approves, or returns it. |
| **QA** | Verifies behaviour and files defects. |
| **OS** | `SystemActor.OS` — infrastructure, deliberately **not** an `ActorRole`. It is the sole permitted initiator of four Task transitions, and has no row in `actors`. |

`Initiator = ActorRole | SystemActor` — anything permitted to request a transition.

## Work

| Term | Meaning |
| :--- | :--- |
| **Feature** | A unit of delivered value. `DRAFT → PLANNED → IN_PROGRESS → IN_VALIDATION → ACCEPTED`. |
| **Feature Plan** | A revision of how a Feature will be built. `DRAFT → READY → ACTIVE → COMPLETED / SUPERSEDED`. |
| **Task** | One piece of work. Ten states, `CREATED` to `ACCEPTED`. |
| **Task Revision** | An immutable attempt at a Task. Never rewritten, carries no status. |
| **Work Package** | What a Worker submits: claims, a verification guide, notes. A hybrid — editable while `DRAFT`, immutable once `SUBMITTED`. |
| **Claim** | A Worker's assertion about what was done. Descriptive; never feeds a deterministic rule. |
| **Evidence** | Proof. `SYSTEM` evidence is generated independently and is the only kind that satisfies a requirement; `WORKER` evidence explains but never proves. |

## Enforcement

| Term | Meaning |
| :--- | :--- |
| **State machine** | Answers *"is this transition defined, and may this initiator request it?"* |
| **Rule Engine** | Answers *"are the conditions this edge declares satisfied by these facts?"* Pure and read-only. |
| **Kernel** | The only component that mutates state, records audit and publishes events. **Checkpoint 6 — does not exist yet.** |
| **RuleContext** | The seven facts supplied to the Rule Engine. It never loads its own. |
| **Transition condition** | A named precondition on an edge. The vocabulary lives in `domain`, so `state` and `rules` can share it without depending on each other. |
| **Rule Coverage Gate** | The blocking precondition on Checkpoint 6: no required condition may be silently unenforced when the Kernel goes live. |

## Persistence and events

| Term | Meaning |
| :--- | :--- |
| **Authoritative state** | Current status of living entities. Carries an optimistic-lock version. |
| **Append-only history** | Inserted, never updated. No version column, no update method, no delete. |
| **`os_events`** | The general event stream. Thirteen closed event types. |
| **`state_transitions_audit`** | Every *evaluated* transition attempt, allowed or rejected, in typed columns. |
| **`sequence_number`** | The sole authority on append order, and a subscriber's resume token. **Not** a QA-result selector. |
| **Wake-up** | A `LISTEN/NOTIFY` signal. Carries an identifier only; the durable stream decides what is processed. |

## Deferred capabilities

**D-1** escalation blocking / a `BLOCKED` state · **D-2** Coordinator lifecycle ·
**D-3** Domain Registry · **D-6** task stop / abandon lifecycle.

All deferred by explicit ruling. None withdrawn, none a Foundation v1 requirement,
and no constraint anywhere admits their states.
