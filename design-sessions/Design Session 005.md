# Design Session 005 – Evidence System

## Purpose of Evidence

Evidence does not prove that work is "done."

Evidence proves that the claims made inside a Work Package are true.

Acceptance is decided later through the engineering workflow.

## Claims

Every Work Package contains one or more Claims.

Examples:

- Login API implemented
- Database migration applied
- Bug fixed
- UI updated

Every Claim requires matching Evidence.

Evidence must directly support the Claim being made.

## Relevant Evidence

Evidence is not classified as "good" or "bad."

Evidence is either:

- Relevant
- Irrelevant

Examples:

Claim:
API implemented

Relevant:

- API response
- Test execution

Irrelevant:

- Screenshot of Git diff

Claim:
Database migration applied

Relevant:

- Database query
- Migration output

Irrelevant:

- API response

## Evidence Standards

Evidence requirements are defined by AI Engineering OS.

Workers do not decide the minimum required Evidence.

Every Worker type follows predefined Evidence Standards.

Example:

Backend Worker

Required:

- API response
- Test execution
- Git diff
- Database verification (when applicable)

Optional:

- Additional logs
- Additional supporting evidence

Workers may provide more Evidence than required.

Workers may never provide less than the required minimum.

## Evidence Sources

Evidence comes from two sources.

### System Evidence

Generated automatically by AI Engineering OS.

Examples:

- Git diff
- Test execution
- API responses
- Build output
- Database verification

System Evidence is:

- Mandatory
- Independent
- Highest trust

### Worker Evidence

Provided by the Worker.

Examples:

- Reasoning
- Design decisions
- Assumptions
- Optional supporting material

Worker Evidence explains the work.

System Evidence proves the work.

## Evidence Verification

Evidence verification is Hybrid.

### Stage 1

AI Engineering OS verifies:

- Required Evidence exists.
- Mandatory checks completed.

If required Evidence is missing, the Work Package is returned before Review.

### Stage 2

Reviewer verifies:

- Evidence actually supports the Claims.
- Evidence is sufficient.

The Reviewer applies engineering judgement.

## Core Principle

Whenever AI Engineering OS can independently verify a Claim, it should.

Independent verification is always preferred over self-reported success.

## Discussion Notes

The discussion concluded that trust comes from independent verification rather than explanations.

System Evidence has higher trust because it is generated independently.

Worker Evidence remains valuable because only the Worker can explain design reasoning and implementation decisions.

Both are required.

## Open Questions

### What should the exact Work Package structure contain?

Status:

Open

Notes:

The Work Package concept now exists.

Its exact schema and fields have not yet been designed.

This becomes the focus of the next checkpoint.
