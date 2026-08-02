# Design Session 004 – Acceptance & Decision Flow

## Acceptance Flow

The accepted engineering flow is:

Worker

↓

Reviewer

↓

QA

↓

Coordinator Acceptance

↓

Builder Approval

↓

Deployment

Deployment is outside engineering.

Engineering ends when the Coordinator accepts the Feature.

Deployment is a Builder decision.

## Reviewer Authority

The Reviewer verifies implementation quality.

The Reviewer may directly return work to the Worker when the requested changes remain within the Worker's authority.

Examples:

- Missing tests
- Small implementation issues
- Coding standard violations
- Minor implementation corrections

If the required change exceeds the Reviewer's authority, the Reviewer escalates to the Coordinator.

Examples:

- Architecture changes
- Shared component modifications
- Business rule uncertainty

## QA Authority

QA validates behavior.

QA does not own business decisions.

QA assigns an initial Severity and Priority to discovered issues.

If the Worker agrees, the issue is fixed.

If the Worker disagrees with QA, the disagreement moves to the Coordinator.

QA and Workers never make the final business decision together.

## Disagreement Resolution

Disagreements always follow the authority chain.

Worker

↓

Coordinator

↓

Orchestrator

↓

Builder (only when business intent changes)

Authority resolves disagreement.

Not seniority.

Not persistence.

## Severity & Priority

QA determines an initial Severity and Priority.

Critical issues may stop the current QA cycle.

Lower-priority issues may continue to be collected into a single report.

The exact Severity/Priority classification system is still open.

## Coordinator Acceptance

The Coordinator owns the Feature.

Reviewer approval and QA approval do not automatically complete a Feature.

The Coordinator confirms that the completed work satisfies the original Feature Brief.

Only then is the Feature accepted.

## Builder Approval

After engineering acceptance, the Feature reaches the Builder.

The Builder decides:

- Deploy now
- Delay deployment
- Bundle with other Features
- Reject deployment

Deployment timing is a product decision, not an engineering decision.

## Discussion Notes

Every role owns one responsibility.

Worker
Owns implementation.

Reviewer
Owns implementation quality.

QA
Owns behavior validation.

Coordinator
Owns Feature completion.

Builder
Owns product and deployment.

This separation of ownership is one of the core principles of AI Engineering OS.
