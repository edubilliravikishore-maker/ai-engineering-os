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
