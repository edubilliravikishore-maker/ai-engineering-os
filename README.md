# AI Engineering OS

## Purpose

Describe the project and provide a durable entry point to its engineering knowledge repository.

## Project Vision

A deterministic operating layer for multi-agent software engineering — one that
enforces the rules of how work gets done, so that trust in the output comes from
the process rather than from any agent's own claim about itself.

The governing principle is [ADR-001](adr/ADR-001.md): **work is never completed by
the agent that performs it.** An agent asserting "I tested it" is not testing it.
The OS exists to make that assertion irrelevant.

> Fuller statements in [docs/00-vision/](docs/00-vision/) — currently drafted from
> the record and awaiting Builder confirmation.

## Mission

Build Foundation v1: a working OS that can carry one Feature from creation to
acceptance, refusing every transition whose conditions are not met and recording
why. See [Mission.md](docs/00-vision/Mission.md).

## Repository Philosophy

The repository explains **why** things exist, not only what they are. Architecture
is frozen in Design Sessions, decisions are recorded in ADRs before the code that
implements them, and rejected directions are preserved rather than deleted.

Two habits follow from that, and both are load-bearing:

1. **Documents come before code.** Every checkpoint lands as two commits — the ADR
   recording the decisions, then the implementation of exactly what it authorised.
2. **Ambiguity is recorded, never absorbed.** When implementation surfaces a
   conflict between authoritative records, it is resolved in an ADR amendment
   rather than settled quietly in a source file.

## Engineering Principles

1. Evolution over replacement.
2. Knowledge over memory.
3. Small focused responsibilities.
4. Everything should be replaceable.
5. Decisions should be documented.
6. Experiments should be preserved.
7. Failures are knowledge.
8. History should never be lost.
9. Documentation is a first-class artifact.
10. The repository should explain not only WHAT exists but WHY it exists.

## Current Status

**Foundation v1 — Checkpoints 1 through 6 delivered. The OS can now enforce.**

```
685 tests passing · ruff clean · mypy clean · 9 migrations applied
```

| # | Checkpoint | Status |
| :--- | :--- | :--- |
| 1 | Scaffolding & tooling | Done |
| 2 | Domain entities & state machines | Done |
| 3 | Rule & policy engine | Done |
| 4 | Persistence & storage | Done |
| 5 | Event store & LISTEN/NOTIFY bus | Done |
| 6 | OS Kernel & transition runner | Done |
| 7 | FastAPI control plane | Not started |
| 8 | Typed client & vertical slice | Not started |

**The Rule Coverage Gate now passes.** It forbade the Kernel operating while any
required transition condition was unenforced ([ADR-004](adr/ADR-004.md) 4.12), and
it was designed to fail from Checkpoint 3 onwards. Twenty-three of the twenty-four
required conditions are enforced by a rule or guaranteed by a domain invariant; the
twenty-fourth is performed by the transition runner itself
([ADR-007](adr/ADR-007.md) 7.5).

**What that means in practice:** the OS refuses a transition whose conditions are
not met, leaves the entity untouched, and records why — durably, in the same
committed transaction that discovered the refusal.

**Start here:** [brain/Project-State.md](brain/Project-State.md) for where things
stand, [brain/Current-Focus.md](brain/Current-Focus.md) for the single next action.

## Roadmap

[docs/05-roadmap/Roadmap.md](docs/05-roadmap/Roadmap.md). Foundation v1 is complete
when the Checkpoint 8 vertical slice runs end to end.

## Repository Structure

| Path | Contents |
| :--- | :--- |
| `src/ai_engineering_os/` | The implementation — `domain`, `state`, `rules`, `storage`, `events`, `core` |
| `tests/` | Unit, integration and architectural boundary tests |
| `migrations/` | Alembic revisions; applied migrations are never edited |
| `adr/` | Architecture Decision Records — the authoritative decision trail |
| `brain/` | Working memory: state, focus, open questions, decision index |
| `docs/` | Vision, architecture, implementation blueprint, protocols, roadmap |
| `design-sessions/` | Design Sessions 001–009 — the frozen architecture |
| `ui/` | The visual layer. Self-contained; see [ui/README.md](ui/README.md) |
| `knowledge/` · `playbooks/` · `templates/` | Reference material and reusable formats |
| `experiments/` · `labs/` · `archive/` | Exploration and preserved history |

### Layers, and what may depend on what

```
domain  ←  state,  rules,  storage,  events
storage ←  events
                        core ← everything
                                     api (CP7) ← core
```

`domain` depends on nothing but Pydantic and the standard library. `rules` must not
import `state`. `storage` must not import `rules`. **Nothing imports `core`** — it
is the only composer, and an import back into it would make the Kernel reachable
from a layer that must not mutate. These are enforced by tests in
`tests/unit/test_domain_isolation.py`, `test_storage_boundaries.py` and
`test_rule_invariants.py`, because the damage from breaking them appears much later
than the mistake.

`ui/` sits outside this graph entirely and imports nothing.

## Documentation Structure

| Path | Contents |
| :--- | :--- |
| `docs/00-vision/` | Vision, Mission, Principles |
| `docs/01-architecture/` | The architecture record |
| `docs/02-implementation/` | The Implementation Blueprint — the working specification |
| `docs/03-protocols/` · `04-memory/` · `07-reference/` | Supporting records |
| `docs/05-roadmap/` | Horizon and critical path |
| `docs/06-history/` | Historical record |

## Decision Recording

Architecture decisions live in [`adr/`](adr/README.md) and are indexed with a
one-line summary each in [brain/Decision-Index.md](brain/Decision-Index.md).

An ADR states what was already required, what it clarifies, and what it explicitly
defers. It names what it supersedes. When implementation later contradicts it, the
ADR is **amended in place with a dated amendment** — ADR-003 §3.11, ADR-004
§4.14–4.16 and ADR-006 §6.11 are all examples. Nothing is silently rewritten.

Open questions that must not be answered by accident are tracked in
[brain/Open-Questions.md](brain/Open-Questions.md).

## Knowledge Management

`brain/` is the working memory and the first thing to read in a new session.
`knowledge/` holds durable reference material. `docs/06-history/` and `archive/`
preserve what is no longer current.

**`brain/` going stale is a known failure mode of this project** — it happened once,
through Checkpoint 4, and cost real time. See
[brain/Lessons-Learned.md](brain/Lessons-Learned.md).

## Contribution Philosophy

- Write the ADR before the code.
- Never invent a lifecycle state, rule, condition or vocabulary entry to make an
  implementation work. If one seems necessary, it is a Builder decision.
- Preserve what is replaced. Delete nothing that carries reasoning.
- A limitation is recorded as a limitation, never overclaimed as a guarantee.

## Future Vision

Beyond Foundation v1, deferred by explicit ruling rather than oversight: the
Coordinator lifecycle and Domain Registry (D-2, D-3), escalation blocking (D-1),
the task stop/abandon lifecycle (D-6), and the Feature-level consequence of plan
supersession. None is withdrawn; none is a Foundation v1 requirement.

The [UI](ui/README.md) goes live once Checkpoints 6 and 7 exist to feed it.
