# Design Session 008 – Orchestrator Lifecycle & Decision Flow

## Purpose

The Orchestrator is the highest engineering-level coordination authority below the Builder.

It handles decisions that exceed a Coordinator's authority, especially decisions involving multiple domains, cross-feature impact, or system-level consequences.

The Orchestrator does not perform implementation work.

## Event-Driven Orchestrator

The Orchestrator is event-driven.

It does not continuously poll Coordinators or Workers.

The Orchestrator wakes only when its authority or information is required.

Examples:

- Builder sends a request.
- Coordinator escalates a system-level decision.
- Cross-domain conflict requires resolution.
- Major system-level issue requires investigation.

Normal Worker and Task events remain with the Coordinator.

A normal Task completion does not automatically wake the Orchestrator.

## Builder Communication

The Builder communicates through the Orchestrator.

Normal Builder requests do not bypass the Orchestrator and directly contact Coordinators or Workers.

The purpose is to preserve:

- Context
- Traceability
- Decision history
- Authority boundaries

The Orchestrator determines how the request affects the relevant Coordinators.

## Coordinator Escalation

A Coordinator escalates when a problem exceeds its authority.

The Coordinator does not simply forward an unresolved problem.

It provides the relevant analysis through the system.

Examples:

- Cross-domain impact
- Persistent unresolved disagreement
- System-level architecture impact
- Requirement ambiguity beyond the Coordinator's authority

The Orchestrator then investigates and makes the system-level decision when possible.

## Decision Request

The Coordinator does not manually construct a large decision package.

The Coordinator emits an escalation event.

AI Engineering OS constructs the structured Decision Request from existing system information.

Relevant information may include:

- Feature
- Task
- Revisions
- Work Packages
- Evidence
- Previous decisions
- Affected domains
- Coordinator analysis
- Coordinator recommendation

The OS must not invent missing information.

Missing information remains explicitly missing.

## Cross-Domain Analysis

When multiple Coordinators or domains are affected, the Orchestrator evaluates the impact before making a decision.

If Coordinators disagree, disagreement alone is not treated as sufficient evidence for a decision.

The affected Coordinators provide:

- Evidence
- Impact analysis
- Risks
- Recommendations

The Orchestrator compares the available information and evaluates system-wide consequences.

If the analysis reveals additional affected domains, those domains are also included in the analysis.

The Orchestrator continues until the relevant impact is understood sufficiently for a decision.

## Orchestrator Decision

When the Orchestrator has sufficient authority and evidence, it makes the system-level decision.

The decision is recorded by AI Engineering OS.

The recorded decision contains, where applicable:

- Decision
- Evidence considered
- Alternatives
- Impact
- Reasoning
- Affected Coordinators
- Final outcome

The decision becomes the authoritative system decision.

The Orchestrator does not need to individually distribute the decision.

AI Engineering OS distributes the recorded decision to affected Coordinators.

## Acknowledgement

A Coordinator receiving an Orchestrator decision acknowledges receipt.

Acknowledgement means:

- The Coordinator received the decision.
- The Coordinator understands the decision.

Acknowledgement does not mean agreement.

The OS records the acknowledgement.

The Coordinator then acts according to the decision.

The OS maintains workflow state rather than requiring agents to remain continuously active while waiting.

## Disagreement

A Coordinator may disagree with an Orchestrator decision.

The Coordinator receives one formal opportunity to present:

- Evidence
- Research
- Risks
- Recommendation

The Orchestrator reviews the additional information.

The Orchestrator may:

- Change the decision.
- Keep the existing decision.

If the Orchestrator keeps the decision, the Coordinator follows it and the disagreement remains recorded as part of the decision history.

New material evidence may justify reconsideration.

The system must not create endless agent-to-agent arguments.

## Orchestrator Uncertainty

The Orchestrator must not guess when a decision exceeds its authority or available evidence.

If the Orchestrator cannot safely resolve the decision, it escalates to the Builder.

The escalation should contain:

- Problem
- Affected domains
- Available options
- Evidence
- Risks
- Recommendations
- Orchestrator analysis
- Reason the Orchestrator cannot safely decide

The Builder makes the decision when the issue reaches business or higher authority.

## Changed Direction During Active Work

An Orchestrator decision may invalidate work that is currently in progress.

The OS must prevent affected Workers from continuing knowingly invalid work.

The current Task/work must be preserved.

The affected Task may become blocked or waiting while the Coordinator evaluates it.

The Worker does not immediately abandon the current work and start another Task.

The Coordinator determines whether the existing work should:

- Resume
- Be reused
- Be abandoned
- Be redirected

The Worker then determines implementation-level details, including which existing implementation components can safely be reused.

## Implementation Boundary

The Orchestrator decides system-level direction.

The Coordinator manages Feature and Task execution.

The Worker understands implementation details.

A higher-level decision does not automatically grant a Worker authority to make every technical change required by that decision.

For example:

If a Worker discovers that a new direction requires a shared API or architecture change, the Worker reports the discovery.

The Worker does not independently modify the shared architecture.

The issue follows the authority chain.

## Core Principle

Agents communicate through structured system state and events rather than uncontrolled agent-to-agent conversation.

AI Engineering OS is the system of record.

The system should preserve:

- Decisions
- Evidence
- Revisions
- Acknowledgements
- Impact analysis
- Disagreements
- Final outcomes

## Open Questions

### How should the Orchestrator's knowledge and context be provided?

Status: Open

Notes:

The Orchestrator's decision and escalation flow has been defined.

The mechanism for providing the Orchestrator with the appropriate organizational knowledge, engineering standards, and context has not yet been designed.

This will be addressed in a future checkpoint.
