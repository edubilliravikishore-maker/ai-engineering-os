# Design Session 007 – Coordinator Lifecycle

## Purpose

The Coordinator behaves as a Technical Lead rather than a manager.

The Coordinator owns Feature delivery.

The Coordinator is responsible for planning work, coordinating execution, tracking progress, and determining when a Feature is ready for acceptance.

The Coordinator does not perform implementation.

## Responsibilities

The Coordinator:

- Understands the Feature goal.
- Identifies required capabilities.
- Identifies task dependencies.
- Creates Tasks.
- Assigns Tasks.
- Tracks Feature progress.
- Accepts completed Features.

The Coordinator never performs implementation work.

## Implementation Boundary

The Coordinator plans work.

The Worker plans implementation.

The Coordinator does not:

- Explore the repository.
- Inspect existing code.
- Decide implementation details.
- Choose libraries or technical approaches.

Repository exploration belongs entirely to the Worker.

## Task Planning

The Coordinator creates Tasks only when all dependencies required for that Task have been satisfied.

Tasks are not created simply because they may be needed later.

Examples:

Backend and Frontend may begin together when independent.

QA begins only after its required dependencies have completed.

Task creation is dependency-driven.

## Event Driven Execution

The Coordinator is event-driven.

The Coordinator remains idle until a meaningful engineering event occurs.

Examples:

- Feature created.
- Worker completed.
- Review completed.
- QA completed.
- Task rejected.

The Coordinator wakes only when required.

## Event Context

Every event contains sufficient context for the Coordinator.

Examples include:

- Feature ID
- Task ID
- Revision ID
- Current status

The Coordinator evaluates only the affected Feature.

It does not scan unrelated Features.

## Feature Health

The Coordinator monitors Feature health throughout execution.

Normal engineering iteration is expected.

Rejected revisions do not automatically indicate failure.

The Coordinator looks for patterns such as:

- Repeated disagreement.
- Lack of progress.
- Repeated failures of the same kind.
- Requirement instability.

When normal engineering no longer resolves the Feature, the Coordinator escalates.

## Escalation

The Coordinator does not escalate because a fixed retry count has been reached.

Escalation occurs when the Coordinator determines that the Feature requires a higher-level decision.

Examples include:

- Persistent engineering deadlock.
- Cross-feature impact.
- Requirement ambiguity.
- Repeated unresolved disagreement.

The Coordinator escalates to the Orchestrator.

## Core Principle

The Coordinator understands the Feature.

The Worker understands the implementation.

Planning and implementation remain separate responsibilities.

## Open Questions

### How should the Orchestrator make cross-feature decisions?

Status:

Open

Notes:

The Coordinator lifecycle has now been defined.

The Orchestrator's authority, responsibilities, and decision process remain undefined.

This becomes the focus of the next checkpoint.
