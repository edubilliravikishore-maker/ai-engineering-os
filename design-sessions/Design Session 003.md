# Design Session 003 – Worker Lifecycle

## Worker Lifecycle

We concluded that a Worker follows this lifecycle:

Receive Task

↓

Explore

↓

Internal Planning

↓

Implementation

↓

Self Recovery

↓

Escalation (only if required)

↓

Produce Work Package

## Exploration

A Worker never starts coding immediately.

The Worker first explores the project to understand existing implementations.

Examples:

- Existing APIs
- Existing database structures
- Existing shared utilities
- Existing authentication
- Existing reusable components

The goal is to reuse existing work instead of creating duplicates.

Exploration is an internal activity.

Normal exploration is not reported.

## Internal Planning

After exploration, the Worker decides its implementation approach.

This planning is internal.

It does not need to be reported unless an exception occurs.

The Worker chooses reuse before new implementation.

## Self Recovery

During implementation, Workers are expected to solve normal engineering problems themselves.

Examples:

- Wrong implementation approach
- Missed dependency
- Existing helper discovered later
- Better reuse opportunity

Workers should rethink and recover before escalating.

## Escalation

Workers do not escalate because they are stuck.

Workers escalate only when the problem exceeds their authority.

Examples:

- Architecture decision required
- Business requirement unclear
- Cross-feature impact
- Shared component change
- Existing feature conflicts with requested feature

Every escalation should include:

- Problem
- Recommendation
- Reasoning
- Evidence
- Estimated impact

## Work Package

When implementation is complete, the Worker produces a Work Package.

The Work Package is the handover object to the next stage.

It contains implementation details needed by downstream workers such as Reviewer, QA, or another technical worker.

The Work Package is not a feature specification.

The Feature Specification comes from the Coordinator before implementation begins.

## Immutability

A submitted Work Package is immutable.

Workers cannot edit or replace a submitted Work Package.

If QA, Review, or the Coordinator finds an issue:

- A new task is created.
- The Worker produces a new Work Package.

History must remain preserved.

## Discussion Notes

We concluded that AI Engineering OS should minimize unnecessary communication.

Workers continue independently during normal work.

Only exceptions move upward.

Routine implementation details remain internal to the Worker.
