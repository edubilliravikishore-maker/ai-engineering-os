# Principles

## Purpose

The principles that govern how this project is built, and how its architecture
behaves. Repository principles shape the record; system principles shape the code.

## Repository principles

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

## System principles

**Independent verification.** No agent completes, approves or accepts its own work
([ADR-001](../../adr/ADR-001.md)). Only independently generated `SYSTEM` evidence
satisfies an evidence requirement; a Worker's own account explains but never proves.

**Validation before mutation.** Conditions are evaluated *before* anything changes.
A refused transition leaves the entity untouched and still commits a durable record
of the refusal, so a rejection can never be lost to a rolled-back mutation.

**Fail closed.** An undefined standard blocks; it never reads as "nothing required".
An evidence standard that has not been ruled refuses the transition rather than
waving it through.

**Determinism.** Explicit typed rules. No DSL, no expression language, no model
judging whether a rule passed. Rules are pure and read-only, and never load their
own facts.

**History is additive.** Append-only tables are inserted, never updated. No generic
delete exists anywhere, so audit history cannot be destroyed through the
persistence layer.

**One component mutates.** Only the Kernel changes state, records audit and
publishes events. The state machine answers whether a transition is defined; the
Rule Engine answers whether its conditions hold; neither acts.

**Complexity must be earned.** Every table, index, channel and abstraction has to
justify itself against a real requirement.

**Limitations are recorded, not overclaimed.** Where a guarantee holds only by
construction rather than by enforcement, the record says so plainly.

**Vocabulary is never invented to unblock an implementation.** No lifecycle state,
rule, condition or role is added for convenience. If one seems necessary, it is a
Builder decision.
