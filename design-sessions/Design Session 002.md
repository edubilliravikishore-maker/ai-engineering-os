# Design Session 002 – Task Lifecycle

## Summary

Today's discussion established how work is decomposed and assigned inside AI Engineering OS.

## Feature vs Task

A Feature is not the same as a Task.

A Feature is a business capability requested by the user.

Examples:

- Login
- Forgot Password
- Attendance
- Inventory

A Feature is owned by a Coordinator and is divided into Tasks.

## Task

A Task is the smallest unit of work assigned to exactly one Worker.

Examples for the Login feature:

- Backend Login
- Frontend Login
- QA Login

A Task belongs to exactly one Worker. A Worker may modify multiple folders while completing a Task.

Workers are not divided by folders such as:

- Routes
- Services
- Database

Instead, Workers own technical implementation.

## Capabilities

The Coordinator first determines which capabilities are required.

Examples:

- Frontend only
- Backend + Frontend
- Backend + Frontend + QA

Workers are selected based on required capabilities rather than Task size.

## Dependencies

Parallel work is possible when dependencies are understood.

For example, Frontend may begin before Backend finishes if the UI contract is already known.

Unknown Features may require the Coordinator to reduce uncertainty before assigning work.

## Authority

Workers make implementation decisions. Workers do not make architecture or product decisions.

When work exceeds a Worker's authority, the Worker provides:

- Recommendation
- Reasoning
- Evidence
- Estimated impact

The Coordinator decides if it remains within the Feature. Otherwise, it is escalated.

## Communication

Workers may communicate directly for small technical dependencies.

Examples:

- API endpoint
- JSON response
- Contract clarification

Major design changes or Feature-impacting decisions are escalated to the Coordinator. Cross-Feature decisions are escalated to the Orchestrator. Business decisions are escalated to the Builder.

This discussion records an engineering design checkpoint and may evolve in future sessions.
