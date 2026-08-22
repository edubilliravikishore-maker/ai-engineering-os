# Development Resources

## Status
Active working document.

## Purpose
Track the development tools and AI models currently available to the Builder/team while developing AI Engineering OS, and establish clear principles for selecting the most appropriate tool and model for each engineering task.

> [!NOTE]
> **This document is NOT an architecture decision.**
> It records tooling available to the Builder during the construction of the system. The AI Engineering OS runtime architecture remains strictly provider- and runtime-agnostic.

---

## Current Development Resources

### 1. Antigravity
- **Access / Environment:** Available directly within the user's development environment.
- **Available Models (Known / Visible):**
  - Gemini 3.7 Flash
- **Profile:** Fast, highly integrated workspace environment with agentic coding capabilities, subagents, and filesystem tools.

### 2. Claude Code
- **Access / Environment:** Active $20 Claude subscription with access to Claude Code CLI.
- **Available Models:** Claude models accessible via the Claude Code subscription.
- **Profile:** Specialized for command-line agentic coding, deep reasoning, multi-file code editing, and architectural analysis.

### 3. Codex CLI
- **Access / Environment:** Access to Codex CLI without a paid subscription (limited / free-tier quota).
- **Profile:** Available but quota-constrained development resource. Best suited for focused, lightweight, or targeted generation tasks where quota limits will not block execution.

---

## Resource Selection Principle

Do not assume a single AI provider or model should be used for every task.

When a development task is planned, the Builder and assistant must evaluate the specific task requirements against available resources to recommend the most effective tool and model.

### Key Evaluation Factors
- **Task Complexity:** Straightforward repetitive edits vs. deep conceptual/algorithmic design.
- **Repository Size & Scope:** Single-file targeted patch vs. broad multi-directory refactoring.
- **Multi-File Changes:** Cross-module changes requiring broad project context.
- **Architecture Sensitivity:** High-stakes foundational decisions vs. routine utility code.
- **Task Type:** Code generation, refactoring, debugging, exploration, test generation, documentation.
- **Reasoning Depth:** Tasks demanding rigorous step-by-step logic vs. standard pattern matching.
- **Context Requirements:** Amount of contextual memory or token window needed.
- **Cost & Token Economics:** Expected token consumption and cost efficiency.
- **Tool / Model Availability & Quotas:** Current operational status and remaining usage limits.

The goal is to allocate development resources intelligently rather than defaulting to a single provider out of habit.

---

## Working Rule for Prompts & Recommendations

When proposing future development steps, prompts, or execution plans, the assistant must provide concrete resource recommendations justified by task characteristics:

- *"Use Claude Code with [appropriate model] for this task because [specific rationale, e.g., complex multi-file refactoring, deep architectural reasoning]..."*
- *"Use Antigravity with [appropriate model] because [specific rationale, e.g., fast iteration, integrated workspace exploration]..."*
- *"Use Codex for this focused task because [specific rationale, e.g., isolated script generation within free quota]..."*

**Rule:** Never recommend a provider merely because it is familiar. Ground every recommendation in task fit and current resource constraints.

---

## Resource vs. Architecture Separation

These development resources are strictly **construction-time tools** for the Builder and are **not** components of the AI Engineering OS runtime architecture.

- The OS runtime architecture must remain completely provider- and runtime-agnostic.
- Current access to Claude Code, Antigravity, or Codex does not imply or create any architectural dependency in the OS itself.

---

## Maintenance & Changes Over Time

This document is a living record and must be updated whenever:
- A new development tool or platform becomes available.
- A model becomes available, updated, or deprecated.
- Subscription tiers or access permissions change.
- Usage quotas or rate limits change significantly.
- A resource is retired or becomes unavailable.
- The Builder explicitly updates development resource preferences.

Temporary tool or model availability must never be treated as a permanent architectural decision.
