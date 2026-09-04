# Vision

> **DRAFT — 2026-09-04.** Written from what the repository already records: ADR-001,
> Design Sessions 001–009, and the Implementation Blueprint. **The Builder has not
> yet ruled on this wording.** It is here because an empty vision page is what let
> the project drift once already. Correct it freely.

## Vision Statement

**A deterministic operating layer for multi-agent software engineering, where trust
in the output comes from the process rather than from any agent's claim about
itself.**

An agent that says "I tested it" has not tested it. AI Engineering OS makes that
sentence irrelevant: work advances only when independently generated evidence
satisfies conditions the system checks, and it is accepted only by someone other
than whoever produced it.

## Context

The governing principle is [ADR-001](../../adr/ADR-001.md): **work is never
completed by the agent that performs it.** Everything else follows.

- **Self-verification is a trust problem, not a workflow preference.** So the OS
  separates who does the work, who checks it, and who accepts it — structurally,
  not by convention.
- **The OS enforces; it does not manage.** It is not an AI manager and does not
  supervise by polling. It answers whether a transition is permitted, records what
  happened, and wakes whoever needs to act.
- **Determinism over judgement.** Rules are explicit typed Python — no DSL, no
  expression language, no model deciding whether a rule passed. Descriptive text
  written by an agent never feeds a deterministic check.
- **The record is the product.** History is additive and never rewritten. A refused
  transition leaves a durable, structured account of what was attempted and which
  rule refused it, which the requesting actor cannot erase.
- **Human authority is preserved where it matters.** The Builder decides what no
  agent may decide, and the architecture repeatedly refuses to settle those
  questions on its own.

## What this is not

Not an agent framework, not a prompt library, not a model router. It takes no view
on which model does the work. It is the layer that decides whether the work counts.
