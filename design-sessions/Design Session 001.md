# Design Session 001 – What Does "Done" Mean?

## Summary

The initial workflow proposed was:

Worker
↓

Evidence Collection
↓

Review
↓

QA
↓

Human Approval
↓

Merge

Worker, Review, QA, and Human Approval are separate so that the agent performing the work does not verify its own work. This creates independent verification, keeps the review surface smaller, and retains human authority over important decisions.

The discussion distinguished between work that is built correctly and work that should be built. Review and QA assess whether the work was built correctly; Human Approval determines whether it should be built.

No agent declares work "done." An agent only declares work ready for the next stage. Work is done when it has been accepted.

## Feature Ownership vs Technical Ownership

During today's discussion we realized that responsibilities should not be divided by source-code folders.

We initially considered workers such as:

- Route Worker
- Service Worker
- Database Worker

This approach was rejected because ownership becomes fragmented and no single worker owns the complete feature.

Instead we agreed on responsibility-based ownership.

A Coordinator owns a business feature such as:

- Authentication
- Inventory
- Payroll
- Attendance

The Coordinator plans the work but does not write code.

Workers own technical implementation.

Examples:

Backend Worker

- APIs
- Business logic
- Database changes
- Validation
- Integrations

Frontend Worker

- UI
- Forms
- API integration
- Client validation

QA Worker

- Functional testing
- End-to-end verification

A technical worker may modify multiple folders if required to complete the feature.

The division is based on responsibility, not file structure.

This discussion is exploratory and may evolve in future sessions.
