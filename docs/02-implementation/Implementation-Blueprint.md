# AI Engineering OS: Foundation v1 Implementation Blueprint

## Status
- **Author:** Antigravity (Advanced Agentic Coding)
- **Status:** Draft / Pending Review
- **Target Release:** Foundation v1
- **Architecture Baseline:** Design Sessions 001–009, ADR-001, ADR-002

---

## Executive Summary

This document establishes the concrete, step-by-step engineering blueprint for implementing **Foundation v1** of **AI Engineering OS**. 

AI Engineering OS is the deterministic operating layer that surrounds the multi-agent engineering workflow. It is **not** an AI manager, supervisor, or reasoning agent. It is the authoritative infrastructure responsible for:
- State management and atomic lifecycle transitions
- Deterministic rule and permission enforcement
- Immutable revision preservation and evidence tracking
- Append-only event persistence and reactive dispatch
- Providing a provider-agnostic control plane for human Builders and AI agents (Orchestrators, Coordinators, Workers, Reviewers, QA)

This blueprint translates the frozen architecture from Design Sessions 001–009 and the technology choices from ADR-002 into a working, testable, modular monolith.

---

## 1. Current Repository Analysis

### 1.1 What Already Exists
- **Architecture & Design Baseline:** Complete conceptual foundation documented across [Design Sessions 001–009](../../design-sessions/README.md), defining feature/task decomposition, worker lifecycles, evidence standards, work package schemas, coordinator/orchestrator authority, and deterministic OS enforcement.
- **Architecture Decision Records:**
  - [ADR-001: Work Is Never Completed By The Agent That Performs It](../../adr/ADR-001.md) (independent verification invariant).
  - [ADR-002: Implementation Foundation & Technology Stack](../../adr/ADR-002.md) (Python 3.13+, FastAPI, Pydantic, PostgreSQL, SQLAlchemy, Alembic, PostgreSQL LISTEN/NOTIFY, Docker Compose, pytest, Ruff, mypy).
- **Operational Memory & Tooling Principles:** [brain/Development-Resources.md](../../brain/Development-Resources.md) tracking development tools available during construction while maintaining strict runtime provider independence.
- **Directory Structure:** Top-level documentation and governance skeleton (`adr/`, `brain/`, `design-sessions/`, `docs/`, `experiments/`, `labs/`, `founders/`, `knowledge/`, `playbooks/`, `prompts/`, `reference/`, `templates/`, `weekly/`).
- **Configuration Scaffolding:** Baseline `.gitignore` configured for operating systems, IDEs, Python artifacts (`.venv`, `__pycache__`), logs, and local environments.

### 1.2 What Can Be Reused
- **Architectural Invariants:** Strict separation of responsibilities (Builder, Orchestrator, Coordinator, Worker, Reviewer, QA), independent verification, and deterministic OS transition gating.
- **Documentation Standards:** Markdown formatting, ADR structure, and explicit decision recording.
- **Development Tooling Principles:** Task-based AI tooling selection without hard-coding providers into OS runtime code.

### 1.3 What Is Missing (To Be Built in Foundation v1)
- **Application Source Code:** No runtime codebase exists under `src/` or `ai_engineering_os/`.
- **Database & Persistence Layer:** No PostgreSQL schema, SQLAlchemy models, session management, or Alembic migrations exist.
- **Domain & State Machine Models:** No runtime domain entities (Feature, Task, WorkPackage, Evidence, Decision) or state transition engines exist.
- **Rule & Policy Enforcement Engine:** No deterministic validators for evidence presence, permissions, or transition criteria exist.
- **Event Bus & Notification Infrastructure:** No event store or PostgreSQL LISTEN/NOTIFY publishing/subscription mechanisms exist.
- **API / Control Plane:** No FastAPI routers, dependency injection, or request schemas exist.
- **Testing & Verification Suite:** No pytest suite, fixtures, or vertical-slice integration tests exist.
- **Container & Environment Setup:** No `docker-compose.yml`, `Dockerfile`, or dependency configuration (`pyproject.toml`) exist.

### 1.4 Existing Conventions to Preserve
- **Complexity Must Be Earned:** Use the smallest reliable infrastructure that satisfies OS invariants (ADR-002). No premature adoption of Redis, Kafka, RabbitMQ, Temporal, or Kubernetes.
- **History Is Additive:** Never overwrite or mutate historical records, revisions, decisions, or events.
- **Provider Independence:** Core OS code must never depend on or hard-code proprietary AI model SDKs.

---

## 2. Implementation Architecture

### 2.1 Runtime Structure: Modular Monolith
Foundation v1 will be implemented as a **Modular Monolith** in Python 3.13+. A modular monolith provides strict internal boundaries, rapid development ergonomics, and zero distributed system overhead while preserving clean domain separation for future scaling.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AI ENGINEERING OS                             │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    API / Control Plane (FastAPI)                  │  │
│  │     - Feature Endpoints         - Work Package Submissions        │  │
│  │     - Task Endpoints            - Review & QA Endpoints           │  │
│  └───────────────────────────────────┬───────────────────────────────┘  │
│                                      │                                  │
│  ┌───────────────────────────────────▼───────────────────────────────┐  │
│  │                           OS Kernel                               │  │
│  │  ┌─────────────────────────┐     ┌─────────────────────────────┐  │  │
│  │  │  State Machine Runner   │     │   Rule & Policy Engine      │  │  │
│  │  │ (Validates Transitions) │     │ (Evidence & Authority Rules)│  │  │
│  │  └────────────┬────────────┘     └──────────────┬──────────────┘  │  │
│  │               │                                 │                 │  │
│  │               └────────────────┬────────────────┘                 │  │
│  │                                │                                  │  │
│  │  ┌─────────────────────────────▼───────────────────────────────┐  │  │
│  │  │                  Domain Model & Entities                    │  │  │
│  │  │    Feature • Feature Plan • Task • Task Revision            │  │  │
│  │  │    Work Package • Evidence • QA Report • Decision           │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────┬───────────────────────────────┘  │
│                                      │                                  │
│  ┌───────────────────────────────────▼───────────────────────────────┐  │
│  │                     Persistence & Event Layer                     │  │
│  │  ┌──────────────────────────────┐ ┌────────────────────────────┐  │  │
│  │  │   SQLAlchemy Repositories    │ │    PostgreSQL Event Store  │  │  │
│  │  │   (Relational / Revisions)   │ │    & LISTEN/NOTIFY Bus     │  │  │
│  │  └──────────────┬───────────────┘ └─────────────┬──────────────┘  │  │
│  └─────────────────┼───────────────────────────────┼─────────────────┘  │
└────────────────────┼───────────────────────────────┼────────────────────┘
                     │                               │
                     ▼                               ▼
       ┌───────────────────────────────────────────────────────────┐
       │                 PostgreSQL 16+ (System of Record)         │
       │    • Relational State (Features, Tasks, Revisions)        │
       │    • Append-Only Event Store (os_events)                  │
       │    • Immutable Evidence & QA Reports                      │
       │    • Audit Logs & State Transitions                       │
       └───────────────────────────────────────────────────────────┘
```

### 2.2 Layer Responsibilities
1. **API / Control Plane Layer (`api`):** Exposes typed REST endpoints for external actors (Builder, Orchestrator, Coordinator, Worker, Reviewer, QA). Extracts caller identity/role, parses Pydantic payloads, and delegates commands to the OS Kernel.
2. **OS Kernel Layer (`core`):** Drives atomic execution of workflow commands. Coordinates the State Machine Runner, Rule Engine, and Unit of Work within transactional boundaries.
3. **Domain Layer (`domain`):** Pure Python / Pydantic models containing business invariants, entity relationships, and value objects. Contains zero database or network I/O.
4. **State Machine Layer (`state`):** Deterministic transition definitions, state graphs, and transition preconditions for all system entities.
5. **Rule & Policy Engine (`rules`):** Composable rule evaluators that independently verify permissions, mandatory evidence presence, sequential dependencies, and QA exit criteria.
6. **Event & Notification Layer (`events`):** Publishes durable events to the PostgreSQL event store and triggers asynchronous wake-up signals via PostgreSQL `LISTEN/NOTIFY`.
7. **Storage & Persistence Layer (`storage`):** SQLAlchemy ORM mappings, Unit of Work, repositories, and Alembic database migrations.

### 2.3 How the OS Surrounds the Agent Hierarchy
The OS is the operating substrate. Agents do not communicate through unconstrained, peer-to-peer side channels to alter system state. 

```
Builder / Orchestrator / Coordinator / Worker / Reviewer / QA
                            │
                            ▼
              [ OS Structured API Gateway ]
                            │
              [ Deterministic Rule & State Gate ]
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
      [ Allow Transition ]      [ Reject Transition ]
               │                         │
      • Atomic DB Commit        • Zero State Mutation
      • Append Event Store      • Record Audit Log
      • Wake Next Actor         • Return Explicit Errors
```

### 2.4 Persistence Invariant
PostgreSQL is the single source of truth. All state changes, task revisions, work packages, evidence records, and event logs are committed within atomic database transactions before any notification is published.

---

## 3. Core Modules (Foundation v1)

| Module | Responsibility | What It Owns | What It Must NOT Own | Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| `domain` | Pure business entities and domain invariants | Domain entities, value objects, domain enums, type definitions | I/O, database queries, HTTP routing, LLM logic | None (Pydantic / stdlib only) |
| `state` | Lifecycle state machines and transition graphs | Valid state graphs, transition definitions, state guards | The condition vocabulary itself (owned by `domain`), database sessions, HTTP handlers, agent prompting | `domain` |
| `rules` | Deterministic policy and transition rule validation | Rule engine, rule contract, `RuleContext`, `RuleResult`, evidence validators, authority checkers, condition classification registry | State mutation, DB connection management, lifecycle graphs, **any dependency on `state`** | `domain` |
| `core` | OS Kernel execution and orchestration | Transaction runner, command handlers, enforcement pipeline | Raw SQL queries, HTTP request parsing, agent generation | `domain`, `state`, `rules`, `events`, `storage` (interfaces) |
| `events` | Event definitions, event store, and notification bus | Event models, event serializer, Postgres LISTEN/NOTIFY publisher/listener | Domain business rules, HTTP endpoint logic | `domain`, `storage` |
| `storage` | Relational persistence and migrations | SQLAlchemy models, domain&nbsp;&harr;&nbsp;row mappers, repositories, Unit of Work session management, persistence exceptions, Alembic migrations | Domain logic, agent execution, API schemas, **the business transaction boundary** (ADR-005 5.5), **generic CRUD or delete semantics** (ADR-005 5.4, 5.7), **any dependency on `rules`** | `domain`, SQLAlchemy, Alembic |
| `api` | HTTP REST control plane | FastAPI routers, request/response schemas, auth/role extraction | Direct business logic, direct DB transactions (calls Kernel) | `core`, `domain`, FastAPI, Pydantic |
| `client` | Provider-agnostic SDK for agents and tools | Typed HTTP client, request formatters, response parsers | OS internal state machine execution | `domain`, httpx / requests |

> [!IMPORTANT]
> **Condition vocabulary ownership (ADR-004 4.7).** The `TransitionCondition` vocabulary of named OS validation requirements is owned by **`domain`**. `state` and `rules` are both consumers of it, answering different questions about the same named requirement:
>
> ```
>               domain
>              /      \
>          state      rules
> ```
>
> - `domain` owns the named condition vocabulary.
> - `state` owns lifecycle graphs and transition definitions, and **declares** which conditions govern each edge.
> - `rules` **evaluates** the conditions.
> - **`rules` must not depend on `state`.**
>
> Public re-exports from `state` are preserved for compatibility. Placing the shared vocabulary in the layer both consumers depend on is the only arrangement that satisfies the dependency table above without duplicating it, and a duplicated vocabulary is a vocabulary that will drift.

---

## 4. Domain Model

```
┌──────────────────┐         1..* ┌──────────────────────┐
│     Feature      ├──────────────►     Feature Plan     │
└────────┬─────────┘              └──────────────────────┘
         │ 1
         │
         │ 1..*
┌────────▼─────────┐         1..* ┌──────────────────────┐
│       Task       ├──────────────►    Task Revision     │
└──────────────────┘              └──────────┬───────────┘
                                             │ 1
                                             │
                                             │ 1
                                  ┌──────────▼───────────┐
                                  │     Work Package     │
                                  └──────────┬───────────┘
                                             │ 1
                                             │
                                             │ 1..*
                                  ┌──────────▼───────────┐
                                  │   Evidence Record    │
                                  └──────────────────────┘
```

### 4.1 Conceptual Entities

> [!NOTE]
> Entity clarifications recorded in [ADR-003](../../adr/ADR-003.md) are authoritative for Foundation v1 and are reflected below.

#### 1. Feature
- **Identity:** `id` (UUID), `slug` (string), `title` (string).
- **Core Attributes:** `goal` (text), `requirements` (structured list), `in_scope` (list), `out_of_scope` (list), `acceptance_criteria` (list of testable assertions), `status` (`FeatureStatus`), `coordinator_id` (UUID), `created_at`, `updated_at`.
- **Relationship:** Belongs to one Coordinator; owns 1..* Feature Plans and 1..* Tasks.

#### 2. Feature Plan
- **Identity:** `id` (UUID), `feature_id` (UUID), `revision_number` (int).
- **Core Attributes:** `status` (`PlanStatus`), `required_capabilities` (list, e.g., `["backend", "frontend", "qa"]`), `task_definitions` (list of `TaskDefinition`: `key`, `title`, `capability`, `depends_on`), `created_by` (UUID), `created_at`.
- **Relationship:** Belongs to one Feature; defines planned Tasks.
- **Task Definition Keys (ADR-003 3.8):** `key` is a **plan-local** slug and `depends_on` references other plan-local keys. Dependencies cannot reference OS `TaskId` values because Task identities do not exist at planning time. A plan's key set must be unique, fully resolvable, and acyclic.
- **Planning-Time Task Creation (ADR-003 3.12):** Tasks **may be created from these definitions while the plan is still `DRAFT`**. The definition list remains the planning record and is not rewritten when Tasks appear; each created Task records the definition `key` it came from (§4.1 #3). Creating a Task confers no execution authority — see §5.2 and §5.4.

#### 3. Task
- **Identity:** `id` (UUID), `feature_id` (UUID), `title` (string).
- **Core Attributes:** `capability` (`CapabilityType`: `BACKEND`, `FRONTEND`, `QA`, etc.), `status` (`TaskStatus`), `assigned_worker_id` (UUID, optional), `dependencies` (list of prerequisite Task UUIDs), `active_revision_number` (int), `feature_plan_id` (UUID, **required**), `plan_definition_key` (plan-local slug, §4.1 #2, **required**), `created_at`, `updated_at`.
- **Relationship:** Belongs to one Feature; originates from one Feature Plan definition; owns 1..* Task Revisions.
- **Existence vs Execution Authorization (ADR-003 3.12):** A Task may exist while its originating Feature Plan is still `DRAFT`. **Existence confers no authority to execute.** Execution authorization derives from the originating plan being `ACTIVE` and is enforced on the `-> READY` transition (§5.2). `feature_plan_id` and `plan_definition_key` exist so the OS can evaluate that precondition and so planning history stays traceable; without them the §5.2 rule is unenforceable.
- **Plan Linkage Is Mandatory (ADR-004 4.8):** `feature_plan_id` and `plan_definition_key` are **both required**, not optional. Every Task is therefore traceable:

  ```
  Task  ->  Feature Plan  ->  plan-local Task Definition
  ```

  This is required for both planning history and future execution authorization. A Task that cannot name its originating plan and definition key cannot be authorized, and its planning provenance would be lost.

#### 4. Task Revision
- **Identity:** `id` (UUID), `task_id` (UUID), `revision_number` (int).
- **Core Attributes:** `created_by_worker_id` (UUID), `work_package_id` (UUID, optional), `review_decision_id` (UUID, references `ReviewDecision`, optional), `qa_report_id` (UUID, optional), `created_at`.
- **Invariant:** Strictly additive. History is never overwritten.
- **No Stored Status (ADR-003 3.1):** A Task Revision carries **no** active/superseded marker. The authoritative active-revision pointer is `Task.active_revision_number` (§4.1 #3). Design Session 006's requirement that only one Revision is active at a time is satisfied by **derivation** — the head of a contiguous, append-only history — because storing the marker would require writing to an already recorded Revision, contradicting the append-only invariant in §7.1.

#### 5. Work Package
- **Identity:** `id` (UUID), `task_revision_id` (UUID).
- **Core Attributes:** `summary` (string), `claims` (list of `Claim` objects: `id`, `claim_type`, `description`), `verification_guide` (structured instructions, endpoints, expected outputs), `worker_notes` (design decisions, assumptions), `risks` (optional text), `submitted_at`.
- **Invariant:** Immutable once submitted.
- **Claim Type (ADR-003 3.7):** `claim_type` is a **descriptive, non-enumerated label**. It never feeds a deterministic OS rule; it supports the Reviewer's Stage 2 judgement that evidence actually supports the claim (Design Session 005). Mandatory System Evidence requirements are keyed by **Task/Worker capability**, not by `claim_type`.

#### 6. Evidence Record
- **Identity:** `id` (UUID), `work_package_id` (UUID, optional), `qa_report_id` (UUID, optional).
- **Core Attributes:** `source_type` (`SYSTEM` vs `WORKER`), `evidence_type` (`GIT_DIFF`, `TEST_OUTPUT`, `API_RESPONSE`, `BUILD_LOG`, `DB_VERIFICATION`, `REASONING`), `content` (text, JSON structure, or URI reference), `checksum` (e.g., SHA-256 for integrity verification), `metadata` (command, exit_code, git_hash, timestamp), `verified_by_os` (bool), `created_at`.
- **Invariants:** 
  - Evidence must be durable, retrievable, and integrity-verifiable.
  - System Evidence is generated independently and carries highest trust.
  - Evidence content storage (inline in PostgreSQL vs. referenced storage) is governed by a configurable size threshold (`MAX_INLINE_EVIDENCE_BYTES`) rather than a fixed architectural constraint.

#### 7. QA Report & QA Defect
- **Identity:** `id` (UUID), `feature_id` (UUID), `task_revision_id` (UUID, optional).
- **Core Attributes:** `is_final_pass` (bool), `tested_scope` (list), `results` (list of `TestResult`: `name`, `passed`, `details`), `defects` (list of `QADefect`: `id`, `title`, `severity`, `priority`, `is_blocker`, `status`, `scope_task_id` (UUID, optional), `scope_feature_id` (UUID, optional)), `evidence_ids` (list of Evidence UUIDs), `status` (`QAStatus`: `PASSED`, `FAILED`, `BLOCKED`), `created_at`.
- **Defect Status (ADR-003 3.6):** `status` is `DefectStatus`: `OPEN` / `RESOLVED`. This is the minimum vocabulary that makes Design Session 009's "zero unresolved in-scope defects" machine-computable.
- **Severity & Priority (ADR-003 3.6):** `severity` and `priority` remain **non-empty free-text labels**. Design Session 004 explicitly leaves the classification system open, and no taxonomy is introduced here. They feed Coordinator remediation prioritisation, which is agent judgement rather than deterministic OS enforcement.
- **Defect Scope (ADR-003 3.11, as amended 2026-08-29):** A defect's acceptance impact is **derived by the OS from an explicit structural association**. The OS **never** accepts an `in_scope` boolean from QA. Every defect references either the **Task** it was found against (`scope_task_id`) or the **Feature** directly (`scope_feature_id`) when no Task represents the affected capability. The OS resolves `Defect -> Task -> Feature`, or `Defect -> Feature`. **A defect resolving to a different Feature is out of scope for the Feature being accepted: it is permanently recorded and does not block that Feature** (ADR-004 4.14). Only **genuinely unresolved** scope blocks acceptance.
- **Defect Scope Cardinality (ADR-004 4.8):** Exactly one of the two scope associations may be set, or neither:

  | `scope_task_id` | `scope_feature_id` | Meaning |
  | :--- | :--- | :--- |
  | set | unset | Defect found against a Task; scope resolves `Defect -> Task -> Feature` |
  | unset | set | No Task represents the affected capability; scope resolves `Defect -> Feature` |
  | unset | unset | **Unresolved scope** — valid to record; invalidates a QA Final Pass |
  | set | set | **Rejected at construction** |

  **Both-absent must remain valid** so the unresolved-scope path stays reachable and testable. No trusted `in_scope` boolean exists on the model, and none may be added.
- **QA Final Pass Validity (ADR-003 3.11, as amended 2026-08-29):** If the association is **absent**, or **resolves to no entity**, the defect's scope is **unresolved** and the OS does not guess. A report with `is_final_pass = true` carrying any scope-unresolved defect is **not a valid QA Final Pass**; a Feature Acceptance relying on it is rejected with an explicit reason naming the defect (§5.1). Resolution comes from QA supplying a valid association, never from OS inference. **A different-Feature association is no longer classified as unresolved** — see *Defect Scope* above and ADR-004 4.14.
- **QA History Is Audit History (ADR-004 4.15):** QA Reports are immutable, and **repeat QA is normal** — a report is scoped to a Task Revision, and the §5.1 `IN_VALIDATION -> IN_PROGRESS` rework loop produces more of them. **No record limits a Feature to one QA Report.** **The mechanism that identifies the authoritative / current QA result is UNRESOLVED** (§14 item 18) and **must not be invented during implementation**: no recency ordering, sequence number, timestamp comparison, "latest" marker, `current_report_id`, QA session identity, or persistence query. **Selecting the authoritative result belongs to the Checkpoint 6 Kernel / context loader; the rule layer evaluates the facts it is supplied and takes no view on their cardinality** (ADR-004 4.4, 4.15). A rule that rejected a Feature merely because several reports were supplied would be inventing QA workflow semantics it does not own.
- **Dangling Feature References Are Not Validated (ADR-004 4.16):** A dangling **Task** association *is* detected, because the rule layer is supplied the Tasks needed to check it. A dangling **Feature** association is **not** detectable in Foundation v1 Checkpoint 3: the approved seven-fact `RuleContext` (§11, ADR-004 4.4) supplies only the Feature under acceptance, and **no `known_feature_ids` fact is added**. An existing different Feature and a nonexistent Feature identifier are therefore indistinguishable, and both are treated as out of scope. **The OS does not claim to validate Feature-reference existence at Checkpoint 3.** This must be addressed when the persistence / context-loader layer is designed (§14 item 19).
- **Scope Boundary (ADR-003 3.11):** The OS enforces the **integrity of the relationship**, not the semantic correctness of the judgement behind it. `Feature.in_scope` / `out_of_scope` remain free-text (Design Session 009) and the OS performs **no** text matching against them. Which Task or Feature a defect belongs to remains QA judgement, resolvable by the Coordinator under the Design Session 009 disagreement path.

#### 8. Decision & Decision Acknowledgement
- **Identity:** `id` (UUID), `scope` (`DECISION_SCOPE`: `FEATURE`, `SYSTEM`, `BUSINESS`).
- **Core Attributes:** `decided_by_role` (`ActorRole`), `decided_by_id` (UUID), `problem` (text), `decision_text` (text), `reasoning` (text), `alternatives_considered` (list), `affected_domains` (list), `created_at`.
- **Acknowledgements:** `acknowledgements` (list of `DecisionAcknowledgement`: `actor_id`, `actor_role`, `acknowledged_at`).
- **Scope (ADR-003 3.2):** `Decision` records **architectural, system-level, and business escalation decisions** only (Design Session 008). It is not the record of a code review outcome.
- **Authority:** `FEATURE` scope may be decided by `COORDINATOR`, `ORCHESTRATOR`, or `BUILDER`; `SYSTEM` by `ORCHESTRATOR` or `BUILDER`; `BUSINESS` by `BUILDER` only. This follows the escalation chain in Design Sessions 004 and 008. A `WORKER` holds no decision authority at any scope.

#### 8b. Review Decision
- **Identity:** `id` (UUID), `task_revision_id` (UUID).
- **Core Attributes:** `reviewer_id` (UUID), `outcome` (`ReviewOutcome`: `APPROVED`, `CHANGES_REQUESTED`), `notes` (text, mandatory), `created_at`.
- **Distinct From `Decision` (ADR-003 3.2):** A Review Decision is an **independent review outcome for one Task Revision**. It is deliberately **not** merged into `Decision` (#8): merging would place every routine code review into permanent architectural decision history, and would break decision authority since `REVIEWER` holds authority at no `DecisionScope`.
- **Invariant:** `notes` are mandatory for both outcomes. §5.2 requires review notes for an approval and explicit feedback for a change request.

#### 9. Actor & Agent
- **Identity:** `id` (UUID), `role` (`ActorRole`: `BUILDER`, `ORCHESTRATOR`, `COORDINATOR`, `WORKER`, `REVIEWER`, `QA`), `domain` (optional string), `name` (string), `is_active` (bool).
- **Capabilities (ADR-003 3.9):** `capabilities` (set of `CapabilityType`). A `WORKER` **must** declare at least one capability. Without this field the §5.2 `READY -> ASSIGNED` rule ("Worker ID is active and possesses matching capability") is unenforceable. Task assignment requires an **active Worker whose capabilities include the Task's capability**.
- **Coordinator Lifecycle — Deferred (ADR-003 3.10):** Foundation v1 uses `is_active` only, where `is_active = true` corresponds to Design Session 009 `ACTIVE`. The DS-009 Coordinator lifecycle (`PROPOSED -> APPROVED -> ACTIVE -> SUSPENDED -> RETIRED`), the Domain Registry, and the Builder-approval registration workflow **remain authoritative architecture and are explicitly deferred, not rejected**. They **MUST** be resolved before the Domain Registry is implemented. See §14, item 7.

#### 10. Event & State Transition Audit Record
- **Event:** `id` (UUID), `event_type` (string), `aggregate_type` (string), `aggregate_id` (UUID), `actor_id` (UUID), `actor_role` (string), `payload` (JSONB), `occurred_at`.
- **State Transition Audit:** `id` (UUID), `entity_type` (string), `entity_id` (UUID), `from_state` (string), `to_state` (string), `requested_by` (UUID), `decision` (`ALLOWED` vs `REJECTED`), `rejection_reasons` (list of strings), `timestamp`.
- **Checkpoint Ownership (ADR-005 5.13):** **Both entities are persisted at Checkpoint 5, not Checkpoint 4.** `os_events` belongs with the event layer that writes it, and `state_transitions_audit` — which no checkpoint previously owned — is assigned to Checkpoint 5 alongside it. **Checkpoint 4 creates neither table, neither model, nor an event repository.**

---

## 5. State Machines

### 5.1 Feature Lifecycle State Machine

```
               ┌──────────┐
               │  DRAFT   │
               └────┬─────┘
                    │ Coordinator creates valid Feature Plan
                    ▼
               ┌──────────┐
               │ PLANNED  │
               └────┬─────┘
                    │ Coordinator activates Plan
                    ▼
            ┌───────────────┐
            │  IN_PROGRESS  │◄────────────────────────┐
            └───────┬───────┘                         │
                    │ All implementation tasks passed │ QA finds defects /
                    ▼                                 │ Revision required
            ┌───────────────┐                         │
            │ IN_VALIDATION ├─────────────────────────┘
            └───────┬───────┘
                    │ QA Final Pass passed + Zero Blockers + Coordinator accepts
                    ▼
               ┌──────────┐
               │ ACCEPTED │
               └──────────┘
```

| From State | To State | Requester Role | OS Validation Requirements | Rejection Triggers |
| :--- | :--- | :--- | :--- | :--- |
| `DRAFT` | `PLANNED` | `COORDINATOR` | Valid Feature Plan attached with at least one task definition. | Missing feature plan or empty task list. |
| `PLANNED` | `IN_PROGRESS` | `COORDINATOR` | Plan transitions `READY` -> `ACTIVE` (§5.4). Activation instantiates any task definition that has no Task yet and **authorizes** the plan's Tasks (ADR-003 3.12). | Plan is incomplete or invalid dependencies exist. |
| `IN_PROGRESS` | `IN_VALIDATION` | `COORDINATOR` / `OS` | All implementation tasks have reached `ACCEPTED` status from Reviewer. | Any implementation task is still in progress or rejected. |
| `IN_VALIDATION` | `ACCEPTED` | `COORDINATOR` | 1. All tasks completed.<br>2. Valid `QA Final Pass` exists.<br>3. Zero unresolved defects whose scope resolves to this Feature via `Defect -> Task -> Feature` or `Defect -> Feature` (ADR-003 3.11 as amended; a defect resolving to a **different** Feature is out of scope and does not block — ADR-004 4.14).<br>4. Mandatory evidence attached. | Missing QA Final Pass, unresolved blocker, incomplete task, or a defect whose scope cannot be resolved. |
| `IN_VALIDATION` | `IN_PROGRESS` | `COORDINATOR` / `QA` | QA Report indicates failure or defects requiring new worker tasks. | Transition requested without valid defect findings. |

---

### 5.2 Task Lifecycle State Machine

```
  ┌─────────┐
  │ CREATED │
  └────┬────┘
       │ Dependencies checked
       ├────────────────────────────────────────┐
       │ (Unresolved dependencies)              │ (No dependencies)
       ▼                                        ▼
┌──────────────────────┐                   ┌─────────┐
│ PENDING_DEPENDENCIES │                   │  READY  │
└──────────┬───────────┘                   └────┬────┘
           │ All prerequisite tasks ACCEPTED    │
           └────────────────────────────────────┤
                                                │ Coordinator assigns Worker
                                                ▼
                                           ┌──────────┐
                                           │ ASSIGNED │
                                           └────┬─────┘
                                                │ Worker starts execution
                                                ▼
┌──────────────────────┐                   ┌─────────────┐
│  REVISION_REQUIRED   │                   │ IN_PROGRESS │
└──────────┬───────────┘                   └──────┬──────┘
           │ Worker starts new Revision           │ Worker submits Work Package
           └──────────────────────────────────────┤ (Mandatory evidence verified)
                                                  ▼
                                           ┌───────────┐
                                           │ SUBMITTED │
                                           └─────┬─────┘
                                                 │ OS routes to Reviewer
                                                 ▼
                                           ┌───────────┐
                                           │ IN_REVIEW │
                                           └─────┬─────┘
                         ┌───────────────────────┴───────────────────────┐
                         │ Reviewer approves                             │ Reviewer rejects
                         ▼                                               ▼
                    ┌─────────┐                                ┌───────────────────┐
                    │ IN_QA   │                                │ REVISION_REQUIRED │
                    └────┬────┘                                └───────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │ QA approves                     │ QA finds defect
        ▼                                 ▼
   ┌──────────┐                 ┌───────────────────┐
   │ ACCEPTED │                 │ REVISION_REQUIRED │
   └──────────┘                 └───────────────────┘
```

| From State | To State | Requester Role | OS Validation Requirements | Rejection Triggers |
| :--- | :--- | :--- | :--- | :--- |
| `CREATED` | `PENDING_DEPENDENCIES` | `OS` | Task has prerequisite task IDs. | No dependencies declared. |
| `CREATED` / `PENDING_` | `READY` | `OS` | 1. Originating Feature Plan is `ACTIVE` — `ORIGINATING_PLAN_ACTIVE` (ADR-003 3.12; declared per ADR-004 4.8).<br>2. All declared prerequisite task IDs are in `ACCEPTED` state — `DEPENDENCIES_ACCEPTED`. | Originating Feature Plan is not `ACTIVE`, or a prerequisite task is not `ACCEPTED`. |
| `READY` | `ASSIGNED` | `COORDINATOR` | Worker ID is active and possesses matching capability. | Worker inactive, nonexistent, or wrong capability. |
| `ASSIGNED` | `IN_PROGRESS` | `WORKER` | Requester matches `assigned_worker_id`. | Requester is not assigned worker. |
| `IN_PROGRESS` | `SUBMITTED` | `WORKER` | 1. Work Package present.<br>2. Claims defined.<br>3. Mandatory System Evidence attached.<br>4. Verification guide present. | Missing System Evidence, empty claims, or missing verification guide. |
| `SUBMITTED` | `IN_REVIEW` | `OS` | Automatic routing to assigned Reviewer. | Reviewer unavailable or unassigned. |
| `IN_REVIEW` | `IN_QA` | `REVIEWER` | Reviewer decision is `APPROVED` with review notes. | Missing review decision or unapproved status. |
| `IN_REVIEW` | `REVISION_REQUIRED` | `REVIEWER` | Reviewer decision is `CHANGES_REQUESTED` with explicit feedback. | Missing feedback rationale. |
| `IN_QA` | `ACCEPTED` | `QA` | QA Report records `PASSED` with test execution evidence. | Unresolved defects or missing test evidence. |
| `IN_QA` | `REVISION_REQUIRED` | `QA` / `COORDINATOR` | QA Report records `FAILED` with defect list. | Missing defect descriptions or severity ratings. |
| `REVISION_REQUIRED` | `IN_PROGRESS` | `WORKER` | Worker creates incremented Task Revision (`revision_number + 1`). | Attempting to overwrite existing revision. |

> [!NOTE]
> **No `BLOCKED` state in Foundation v1 (ADR-003 3.3).** The Task lifecycle above is complete and intentionally defines no `BLOCKED` state. Design Session 008 requires that the OS prevent affected Workers continuing knowingly invalid work after an Orchestrator decision; that capability is **deferred** from Foundation v1 and is knowingly unserved (see §14, item 6). The `BLOCKED` reference in the §6 event table is a forward reference to that future capability, not a Foundation v1 state.

> [!NOTE]
> **Task existence is not execution authority (ADR-003 3.12).** A Task may be created while its Feature Plan is still `DRAFT`. Such a Task rests in `CREATED` or `PENDING_DEPENDENCIES` — legitimate resting states for planned-but-unauthorized work, not states that imply imminent execution. It becomes executable only once its originating Feature Plan is `ACTIVE`, enforced on the `-> READY` edge above and nowhere else. **"A Task exists" is not "a Task is authorized to execute."**

> [!WARNING]
> **`ORIGINATING_PLAN_ACTIVE` is declared, not yet enforced (ADR-004 4.8, 4.11).** Checkpoint 3 adds `ORIGINATING_PLAN_ACTIVE` to the condition vocabulary and declares it on **both** `-> READY` edges above. **The rule that evaluates it is deliberately deferred** and sits in `PENDING_RULE_EXPANSION`; ADR-003 3.12 places its enforcement with the Checkpoint 6 transition runner. Until that rule exists, the Rule Engine reports this condition as *unevaluated* on every `-> READY` evaluation rather than passing it silently. The declaration is a domain/state record required by an already-approved decision — **it is not permission to widen the Checkpoint 3 rule set** (§15 Checkpoint 3).

---

### 5.3 Work Package Lifecycle
- **States:** `DRAFT` (Worker local) $\rightarrow$ `SUBMITTED` (OS System of Record) $\rightarrow$ `VALIDATED` $\rightarrow$ `REVIEWED` $\rightarrow$ `ACCEPTED` / `REJECTED`.
- **Invariants:** 
  - A Work Package in `SUBMITTED` status is **immutable**.
  - No actor (including Worker, Reviewer, or Coordinator) can edit a submitted Work Package.
  - Fixes require generating a new Revision and a new Work Package entity.

#### Authority Model (ADR-003 3.5)

The Work Package lifecycle uses a **single authority model**. Only `DRAFT -> SUBMITTED` is actor-requested. Every subsequent state is an **OS projection** of the corresponding Task lifecycle outcome.

| From State | To State | Initiator | Driven By |
| :--- | :--- | :--- | :--- |
| `DRAFT` | `SUBMITTED` | `WORKER` | Task `IN_PROGRESS` -> `SUBMITTED` (§5.2) |
| `SUBMITTED` | `VALIDATED` | `OS` | OS Stage 1 mandatory-evidence validation (Design Session 005) |
| `VALIDATED` | `REVIEWED` | `OS` | Task `IN_REVIEW` -> `IN_QA` / -> `REVISION_REQUIRED` (§5.2) |
| `REVIEWED` | `ACCEPTED` | `OS` | Task `IN_QA` -> `ACCEPTED` (§5.2) |
| `REVIEWED` | `REJECTED` | `OS` | Task -> `REVISION_REQUIRED` (§5.2) |

**Reviewer, QA, and Coordinator hold no independent authority over Work Package state.** The actor performs the action at the Task level; the OS maintains the Work Package projection. Assigning per-role authority here would create a second authority model competing with the Task state machine over the same real-world action, so authority stays defined in exactly one place.

---

### 5.4 Feature Plan Lifecycle

Recorded per ADR-003 3.4. Design Session 009 defines the state chain; the requester authority below is the Foundation v1 clarification.

```
DRAFT ──→ READY ──→ ACTIVE ──→ COMPLETED
                       │
                       └─────→ SUPERSEDED
```

| From State | To State | Requester Role | Notes |
| :--- | :--- | :--- | :--- |
| `DRAFT` | `READY` | `COORDINATOR` | The Coordinator owns the Feature Plan (Design Session 009). |
| `READY` | `ACTIVE` | `COORDINATOR` | Activation is the **authorization boundary** (ADR-003 3.12): it instantiates any task definition that has no Task yet, authorizes the plan's Tasks, and dependency-free Tasks move to `READY`. |
| `ACTIVE` | `COMPLETED` | `COORDINATOR` / `OS` | `OS` only when completion is deterministically derived from prerequisites, mirroring §5.1 `IN_PROGRESS` -> `IN_VALIDATION`. |
| `ACTIVE` | `SUPERSEDED` | `COORDINATOR` | A plan revision supersedes the active plan rather than silently overwriting it (Design Session 009). |

- **Terminal States:** `COMPLETED` and `SUPERSEDED`.
- **Deferred (ADR-003 3.4):** `DRAFT -> SUPERSEDED` and `READY -> SUPERSEDED` are **not** permitted in Foundation v1.
- **Planning-Time Task Creation (ADR-003 3.12):** Tasks may be created against a `DRAFT` plan. They carry no execution authority until this plan reaches `ACTIVE` (§4.1 #3, §5.2).

#### Supersession & Disposition of Unfinished Work (ADR-003 3.13)

When a Feature Plan transitions `ACTIVE` -> `SUPERSEDED`, **the OS performs no automatic routing whatsoever**:

- The superseded Plan and its Tasks remain **immutable history**.
- Existing Tasks are **not** moved to the successor plan.
- Existing Tasks are **not** deleted.
- The OS **does not decide** what happens to unfinished work.

The **Coordinator explicitly decides the disposition of each unfinished Task**, using the vocabulary Design Session 008 already established for work invalidated by a higher-level decision: **resume, reuse, abandon, or redirect**. Useful work may be **represented** as new planned work in the successor plan; it is never migrated. **No automatic migration mechanism exists or may be implemented.**

Two consequences follow without any new mechanism:

1. A Task of the superseded plan that had not yet reached `READY` **simply never becomes authorized** — the §5.2 precondition declines to fire. This is the OS not acting, not the OS deciding; the Task waits for Coordinator disposition.
2. A Task already in execution is **not interrupted by the OS**; it continues under its own lifecycle until the Coordinator dispositions it. **Foundation v1 has no mechanism to halt in-flight work** — see §14, item 6 (`BLOCKED`, deferred).

- **Deferred (D-6):** the persisted record of a disposition decision, any recorded relationship between a superseded plan's Task and successor planned work, and any terminal state for stopped work. See §14, item 11.
- **Open Question — Feature-Level Consequence:** Design Session 009 does not state what happens to the **Feature's own lifecycle status** when its plan is superseded, or how the successor plan revision is instantiated. ADR-003 3.13 resolves the routing of the Plan and its Tasks but **does not decide this**. See §14, item 9. **Unresolved.**

---

## 6. Event Model (Foundation v1)

Every significant OS action generates a structured domain event persisted synchronously into `os_events` before publishing a notification.

```
┌─────────────────────────┐
│       Event Model       │
├─────────────────────────┤
│ id: UUID                │
│ event_type: str         │
│ aggregate_type: str     │
│ aggregate_id: UUID      │
│ actor_id: UUID          │
│ actor_role: str         │
│ payload: JSONB          │
│ occurred_at: timestamp  │
└─────────────────────────┘
```

| Event Type | Producer | Consumer | State Change | Wakes Component? | Meaning / Payload Highlights |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `FeatureCreated` | Builder / Orchestrator | Coordinator | Yes (`DRAFT`) | Coordinator | Feature intent, requirements, and scope registered. |
| `FeaturePlanCreated` | Coordinator | OS / Coordinator | Yes (`PLANNED`) | OS | Feature Plan drafted with initial task definitions. |
| `FeaturePlanActivated`| Coordinator | OS / Workers | Yes (`IN_PROGRESS`) | Workers | Plan activated; the plan's Tasks become authorized (ADR-003 3.12) and dependency-free tasks move to `READY`. |
| `TaskAssigned` | Coordinator | Worker | Yes (`ASSIGNED`) | Assigned Worker | Task assigned to specific technical worker. |
| `TaskStarted` | Worker | OS / Coordinator | Yes (`IN_PROGRESS`) | Coordinator | Worker acknowledges and begins exploration/coding. |
| `WorkPackageSubmitted`| Worker | OS / Reviewer | Yes (`SUBMITTED`) | OS / Reviewer | Worker submits completed revision and evidence. |
| `EvidenceAttached` | Worker / OS / QA | OS | No | None | System/Worker evidence record bound to revision. |
| `StateTransitionAllowed`| OS Kernel | Interested Actors | Yes | Matching Actor | Audit record of successful lifecycle transition. |
| `StateTransitionRejected`| OS Kernel | Requesting Actor | No | Requesting Actor | Audit record of failed transition with failure reasons. |
| `ReviewCompleted` | Reviewer | Coordinator / Worker | Yes (`IN_QA` or `REVISION_REQ`) | Coordinator / Worker | Reviewer outcome (`APPROVED` vs `CHANGES_REQUESTED`). |
| `QAReportSubmitted` | QA | Coordinator / Worker | Yes (`ACCEPTED` or `REVISION_REQ`) | Coordinator / Worker | QA verification results, test runs, and defect list. |
| `FeatureAccepted` | Coordinator | Orchestrator / Builder | Yes (`ACCEPTED`) | Orchestrator / Builder | Feature delivery accepted by Coordinator. |
| `EscalationRaised` | Worker / Coordinator | Higher Authority | No (see ADR-003 3.3) | Orchestrator / Builder | Authority boundary reached; decision requested. Foundation v1 defines **no** `BLOCKED` state; escalation blocking is a deferred capability (§14, item 6). |

---

## 7. Persistence Architecture (PostgreSQL)

### 7.1 Authoritative State vs Append-Only History

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           PostgreSQL Database                            │
│                                                                          │
│   AUTHORITATIVE CURRENT STATE                  APPEND-ONLY HISTORY       │
│  ┌─────────────────────────────┐              ┌────────────────────────┐ │
│  │ actors                      │              │ task_revisions         │ │
│  │ features                    │              │ evidence_records       │ │
│  │ feature_plans               │              │ qa_reports / defects   │ │
│  │ tasks                       │              │ review_decisions       │ │
│  │ work_packages (hybrid)      │              │ decisions / acks       │ │
│  └─────────────────────────────┘              │ os_events         [CP5]│ │
│                                               │ transitions_audit [CP5]│ │
│                                               └────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

1. **Authoritative State:** Relational tables holding the current, active status and relationships of living entities (`features.status`, `tasks.status`, `tasks.assigned_worker_id`).
2. **Append-Only History:** Immutable records capturing the exact sequence of engineering actions, revisions, evidence, and audit decisions.
3. **Insert-Only Enforcement (ADR-003 3.1):** Rows in the append-only tables are **inserted, never updated**. In particular, `task_revisions` rows carry no mutable status column; a Revision is never rewritten or re-marked once recorded. The active-revision pointer lives on `tasks.active_revision_number`, which is authoritative-state, not history.
4. **Actor Persistence (ADR-005 5.1):** A single `actors` table carries `role` as a column. **No `coordinators` table and no Domain Registry persistence is created**, because ADR-003 3.10 forbids it until the Coordinator lifecycle is resolved (§14, item 7). The `coordinators` / `workers` split shown in earlier revisions of this diagram is **superseded**.
5. **`work_packages` Is A Hybrid (ADR-005 5.8):** Earlier revisions of this diagram placed `work_packages` under append-only history, which contradicted the five-value OS projection ADR-003 3.5 requires. **That classification is amended.** A `DRAFT` Work Package remains editable; `SUBMITTED` is persisted as the durable record; **submitted content becomes immutable**; and the **already-approved lifecycle transitions remain the sole authority for status changes**. ADR-003 3.5 is unchanged.
6. **Events And Transition Audit Land At Checkpoint 5 (ADR-005 5.13):** `os_events` and `state_transitions_audit` are marked `[CP5]` above. **Checkpoint 4 creates neither**, and no event repository. `state_transitions_audit`, which no checkpoint previously owned, is assigned to Checkpoint 5 (§15).
7. **Enforcement Mechanism (ADR-005 5.8, 5.14):** Append-only is enforced **by construction** — no repository exposes an update path for a historical table (ADR-005 5.4, 5.7) — not by database trigger. This is a **recorded limitation**, not an independently enforced guarantee in the ADR-001 sense: code holding a raw session could still bypass it.
8. **Optimistic-Lock Versions (ADR-005 5.6):** A version column exists on the authoritative-state tables only — `actors`, `features`, `feature_plans`, `tasks`, `work_packages`. Append-only tables carry none, because a row that is never updated cannot lose an update race.
9. **Persistence Metadata Timestamps (ADR-005 5.9):** Every table carries database-generated persistence metadata timestamps. They are **separate from the domain timestamps**, are **never mapped into domain objects**, and **must not be used for ordering, filtering, or authoritative QA-result selection** (ADR-004 4.15, §14 item 18).

### 7.2 Transactional Transition Boundary & Invariant
All OS state transitions are protected by explicit PostgreSQL ACID transactions.

> [!IMPORTANT]
> **Transaction ownership and concurrency control (ADR-005 5.5, 5.6).**
>
> - **The service/use-case layer owns the transaction boundary.** Repositories perform persistence operations and use the session supplied to them; they never open a session, and never call `commit()` or `rollback()`. The `storage` layer owns the Unit of Work mechanism (§2.2); the **Checkpoint 6 Kernel is the transaction owner**, and it does not exist until that checkpoint.
> - **Concurrency control is optimistic locking, not `SELECT FOR UPDATE`.** ADR-005 5.6 supersedes the §14 item 1 recommendation. A version column exists on the authoritative-state tables only. Concurrent modification is **detected and reported** as `ConcurrencyConflictError`, never silently overwritten.
> - **The conceptual snippet below reflects this ruling.** The *Validation-First* sequence it depicts — evaluate before mutating, record the rejection durably, commit — is unchanged and remains authoritative.
> - **Repositories translate infrastructure errors** into `NotFoundError`, `ConcurrencyConflictError`, and `PersistenceError` (ADR-005 5.12). These carry no HTTP status codes; the transport mapping belongs to Checkpoint 7.

**Core Invariant:**
> **Rejected transition = no target-state mutation + durable rejection record.**

To guarantee that the rejection record is never lost due to a rolled-back state mutation, the OS employs a **Validation-First** transactional strategy:
1. State machine rules and policy preconditions are evaluated **before** applying any mutation to the target entity.
2. If validation **fails**:
   - The entity's state is **not mutated** (it remains untouched in its original `from_state`).
   - The rejection audit entry is inserted into `state_transitions_audit` and `os_events` (`StateTransitionRejected`).
   - The transaction containing the rejection record is **committed** to PostgreSQL.
   - The OS returns `422 Unprocessable Entity` with the structured rejection reasons to the requesting actor.
3. If validation **succeeds**:
   - The entity state is mutated to `to_state`.
   - Immutable child records (Work Package, Evidence, Revision) are inserted.
   - The success event (`StateTransitionAllowed` / specific domain event) is inserted into `os_events`.
   - The transaction is **committed**, followed by a post-commit `pg_notify()`.

```python
# Conceptual Transactional Pattern in OS Kernel (Validation-First, optimistic locking)
# The Kernel owns the transaction boundary; repositories use the session it supplies
# and never commit (ADR-005 5.5). Repositories return frozen domain objects,
# never ORM models (ADR-005 5.11), so nothing below holds a live database row.
async with unit_of_work() as uow:
    # 1. Load the domain object. No row lock is taken: the version read here is the
    #    token the commit in step 6 will check (ADR-005 5.6).
    task = await uow.tasks.get_by_id(task_id)        # raises NotFoundError if absent

    # 2. Evaluate State Machine & Rule Engine BEFORE any mutation.
    #    The state machine answers "is this transition defined, and may this initiator
    #    request it?"; the Rule Engine answers "are the declared conditions satisfied
    #    by these facts?" (ADR-004 4.7). The Kernel's context loader assembles the
    #    RuleContext from repositories; the Rule Engine never loads its own facts.
    evaluation = evaluate_transition(
        machine=TASK_STATE_MACHINE,
        current_state=task.status,
        target_state=TaskStatus.SUBMITTED,
        initiator=current_actor.role,
        context=await load_rule_context(uow, task=task, work_package=work_package),
    )

    if not evaluation.is_allowed:
        # State remains unchanged (task is frozen; nothing was mutated).
        # Durably record the rejection audit record and event in this committed transaction.
        await uow.transition_audit.add(
            transition_rejection_record(
                entity_type="Task",
                entity_id=task.id,
                from_state=task.status,
                attempted_state=TaskStatus.SUBMITTED,
                requested_by=current_actor.id,
                reasons=evaluation.rejection_reasons,
            )
        )
        await uow.events.add(state_transition_rejected_event(task, evaluation))
        await uow.commit()
        raise TransitionRejectedException(reasons=evaluation.rejection_reasons)

    # 3. Apply the state change ONLY after validation passes. Domain models are frozen,
    #    so this produces a new object rather than mutating the loaded one.
    submitted_task = task.with_status(TaskStatus.SUBMITTED).with_active_revision(
        revision.revision_number
    )

    # 4. Insert immutable child records (Revision, Work Package, Evidence).
    #    Identities already exist — they were generated by the application (ADR-005 5.9)
    #    so these records can reference each other before anything is written.
    await uow.task_revisions.add(revision)
    await uow.work_packages.add(work_package)
    for record in system_evidence:
        await uow.evidence.add(record)
    await uow.flush()                                 # resolve FKs; nothing committed yet

    # 5. Stage the authoritative-state update and the event.
    await uow.tasks.save(submitted_task)              # carries the version read in step 1
    event = work_package_submitted_event(submitted_task, work_package)
    await uow.events.add(event)

    # 6. Commit. The UPDATE in step 5 matches on the version read in step 1: if another
    #    transaction changed this Task in between, no row matches and the repository
    #    raises ConcurrencyConflictError. Nothing is silently overwritten, and the whole
    #    transaction rolls back (ADR-005 5.6).
    await uow.commit()

# 7. Post-commit notification (LISTEN/NOTIFY)
await notification_bus.emit(channel="task_events", payload={"event_id": event.id})
```

> [!NOTE]
> **Illustrative only.** The names above depict the transactional shape, not a fixed API. The `os_events` and `state_transitions_audit` writes land at Checkpoint 5 ([ADR-005](../../adr/ADR-005.md) 5.13); `load_rule_context` and the transition runner land at Checkpoint 6 ([ADR-004](../../adr/ADR-004.md) 4.4). **Checkpoint 4 builds only the repositories and the session scope this pattern consumes.**

---

## 8. OS Rule & Transition Enforcement

### 8.1 Valid Transition Walkthrough

```
Worker                         OS Control Plane                 PostgreSQL
  │                                    │                            │
  │ 1. POST /tasks/{id}/submit-package │                            │
  ├───────────────────────────────────►│                            │
  │    (Claims, Diff, Test Evidence)   │ 2. Open Transaction        │
  │                                    ├───────────────────────────►│
  │                                    │ 3. Lock Task Row           │
  │                                    │ 4. Check Worker Authority  │
  │                                    │ 5. Check Task State == IN_PROGRESS
  │                                    │ 6. Evaluate Rule Engine:   │
  │                                    │    - SystemEvidenceRule: OK│
  │                                    │    - ClaimMappingRule: OK  │
  │                                    │ 7. Update Task -> SUBMITTED│
  │                                    │ 8. Insert Work Package     │
  │                                    │ 9. Insert Event Record     │
  │                                    │ 10. Commit Transaction     │
  │                                    ├───────────────────────────►│
  │                                    │ 11. PG NOTIFY "task_events"│
  │ 12. 200 OK (Revision #1 Active)    │                            │
  │◄───────────────────────────────────┤                            │
```

### 8.2 Invalid Transition Walkthrough (Rejection)

```
Worker                         OS Control Plane                 PostgreSQL
  │                                    │                            │
  │ 1. POST /tasks/{id}/submit-package │                            │
  │    (Claims present, ZERO Diff/Test)│ 2. Open Transaction        │
  ├───────────────────────────────────►│                            │
  │                                    │ 3. Lock Task Row           │
  │                                    │ 4. Check Worker Authority  │
  │                                    │ 5. Evaluate Rule Engine:   │
  │                                    │    - SystemEvidenceRule: FAIL
  │                                    │      (Missing Git Diff/Test)
  │                                    │ 6. No State Mutation       │
  │                                    │    (Task stays IN_PROGRESS)│
  │                                    │ 7. Insert Rejection Audit  │
  │                                    │    and os_events record    │
  │                                    │ 8. Commit Transaction     │
  │                                    ├───────────────────────────►│
  │ 9. 422 Unprocessable Entity        │                            │
  │    {                               │                            │
  │      "status": "REJECTED",         │                            │
  │      "errors": [                   │                            │
  │        "Missing mandatory System   │                            │
  │         Evidence: git_diff"        │                            │
  │      ]                             │                            │
  │    }                               │                            │
  │◄───────────────────────────────────┤                            │
  │                                    │                            │
  │ (Task remains in IN_PROGRESS;      │                            │
  │  Rejection durably preserved)      │                            │
```

---

## 9. Agent / Runtime Boundary

### 9.1 Strict Provider Independence
The OS does **not** know, care, or depend on whether a calling actor is powered by Claude Code, Gemini, OpenAI Codex, a local model, or a deterministic test script.

- **No AI SDK imports in OS core:** Core OS codebase will never import `anthropic`, `google-genai`, or `openai`.
- **Standard Protocol:** All interactions occur via standard HTTP/JSON REST endpoints.
- **Actor Context Extraction:** Caller identity and authority are passed through standardized request headers:
  - `X-Actor-ID`: UUID of the calling agent or user.
  - `X-Actor-Role`: Role enum (`BUILDER`, `ORCHESTRATOR`, `COORDINATOR`, `WORKER`, `REVIEWER`, `QA`).
  - `X-Domain-ID`: Domain name / identifier (for Coordinators/Workers).

### 9.2 Agent Client Adapter (`ai_engineering_os.client`)
A lightweight, typed Python client library will be provided for use by agent runners, test harnesses, and CLI tools to interact cleanly with the OS API.

---

## 10. First Vertical Slice (Foundation v1)

### 10.1 Purpose & Actor Scope (Minimal / Test Actors)
The primary goal of the first vertical slice is to **prove the OS workflow, deterministic rules, state tracking, and transition enforcement mechanisms**.

> [!IMPORTANT]
> **Foundation v1 does NOT require fully intelligent or LLM-driven Reviewer, QA, Coordinator, or Orchestrator implementations.**
> 
> In this first vertical slice, all actors (Reviewer, QA, Worker, Coordinator) are implemented as **minimal/test actors** (deterministic test harnesses, simulated agent clients, or lightweight API scripts). Their sole purpose is to drive the OS interfaces, submit structured payloads (Work Packages, Evidence, QA Reports), and verify that:
> - The OS deterministically validates rules, permissions, and mandatory evidence.
> - Invalid transitions are rejected with durable rejection audit logs.
> - Valid transitions atomically advance state and publish notifications.
> - Full historical revisions and event logs are preserved.

### 10.2 Vertical Slice Workflow Scenario

```
Step 1: System Boot & Migrations
        PostgreSQL starts -> Alembic applies baseline schema -> OS Kernel boots.

Step 2: Domain Registration
        "auth-domain" registered with Coordinator "auth-coordinator".

Step 3: Feature Creation
        Builder creates Feature: "User Authentication via Email/Password".
        Status: DRAFT.

Step 4: Feature Plan Creation & Activation
        Coordinator drafts Feature Plan defining Task 1: "Implement Auth API".
        Task 1 may exist as planned work while the Plan is DRAFT (CREATED status,
        no execution authority - ADR-003 3.12).
        Plan READY -> ACTIVE -> Task 1 is authorized and moves to READY status.

Step 5: Task Assignment & Start
        Coordinator assigns Task 1 to Worker "backend-worker-1".
        Worker starts Task 1 -> Status: IN_PROGRESS.

Step 6: Invalid Transition Test (Enforcement Proof)
        Worker attempts to submit Work Package with NO System Evidence.
        OS rejects transition (422) -> Rejection recorded in audit log.
        Task remains IN_PROGRESS.

Step 7: Valid Work Package Submission
        Worker attaches System Evidence (Git diff + pytest log) & submits.
        OS validates -> Status: SUBMITTED -> Revision #1 created -> Event emitted.

Step 8: Independent Review
        Reviewer inspects Revision #1 & attached evidence -> Approves.
        Task status -> IN_QA.

Step 9: QA Validation & Final Pass
        QA runs functional suite -> Submits QA Report with 0 defects & test traces.
        QA Final Pass recorded. Task status -> ACCEPTED.

Step 10: Feature Acceptance
        Coordinator requests Feature Acceptance.
        OS validates: All tasks ACCEPTED + QA Final Pass present.
        Feature status -> ACCEPTED.

Step 11: History & Audit Verification
        OS reconstructs full immutable event stream and revision history.
```

---

## 11. Initial Project Structure

> [!NOTE]
> Status markers reflect the repository as of the completion of Checkpoint 3. `[IMPLEMENTED — CPn]` marks code that exists today; `[PLANNED — CPn]` marks the Foundation v1 target for a later checkpoint (§13). Governance and documentation directories not central to the runtime (`archive/`, `assets/`, `experiments/`, `founders/`, `knowledge/`, `labs/`, `playbooks/`, `prompts/`, `reference/`, `templates/`, `weekly/`) are summarized rather than expanded.

```
AI-Engineering-OS/
├── .gitignore
├── .env.example                # Example environment configuration
├── LICENSE
├── README.md
├── pyproject.toml              # Build config, dependencies, ruff, mypy, pytest
├── requirements.txt            # Runtime dependencies (mirrors pyproject.toml)
├── requirements-dev.txt        # Development & quality-check dependencies
├── alembic.ini                 # Database migration config
├── docker-compose.yml          # Local PostgreSQL + OS runtime
├── Dockerfile                  # OS application container
│
├── adr/                        # Architecture Decision Records (ADR-001, ADR-002, ADR-003)
├── brain/                      # Working memory, decision index & open questions
├── design-sessions/            # Frozen architecture design sessions (001–009)
├── docs/                       # Permanent project documentation
│   ├── 00-vision/
│   ├── 01-architecture/
│   └── 02-implementation/
│       └── Implementation-Blueprint.md
│
├── migrations/                 # Alembic migration versions        [IMPLEMENTED — CP1]
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_baseline.py
│
├── src/
│   └── ai_engineering_os/
│       ├── __init__.py                                             [IMPLEMENTED — CP1]
│       ├── main.py             # FastAPI entrypoint                 [IMPLEMENTED — CP1]
│       ├── config.py           # Environment & OS settings          [IMPLEMENTED — CP1]
│       │
│       ├── domain/             # Pure domain entities, value objects, enums  [IMPLEMENTED — CP2]
│       │   ├── __init__.py     # Public domain surface
│       │   ├── base.py         # Frozen DomainModel base & shared value types
│       │   ├── errors.py       # Structured domain errors (no transport concerns)
│       │   ├── identifiers.py  # Strongly typed entity identifiers
│       │   ├── enums.py        # Statuses, Roles, Capabilities, EvidenceTypes
│       │   ├── conditions.py   # TransitionCondition vocabulary (ADR-004 4.7)  [IMPLEMENTED — CP3]
│       │   ├── actor.py        # Actor identity & capability matching
│       │   ├── feature.py      # Feature & Scope models
│       │   ├── plan.py         # FeaturePlan & TaskDefinition models
│       │   ├── task.py         # Task, TaskRevision & TaskRevisionHistory models
│       │   ├── work_package.py # WorkPackage, Claim & VerificationGuide models
│       │   ├── evidence.py     # EvidenceRecord models
│       │   ├── qa.py           # QAReport, QADefect & TestResult models
│       │   └── decision.py     # Decision, Acknowledgement & ReviewDecision models
│       │
│       ├── state/              # State machines & transition definitions      [IMPLEMENTED — CP2]
│       │   ├── __init__.py
│       │   ├── machine.py      # Generic state machine & transition evaluator
│       │   ├── feature_sm.py   # Feature lifecycle graph (§5.1)
│       │   ├── plan_sm.py      # Feature Plan lifecycle graph (§5.4)
│       │   ├── task_sm.py      # Task lifecycle graph (§5.2)
│       │   └── work_package_sm.py # Work Package lifecycle graph (§5.3)
│       │
│       ├── rules/              # Rule validation engine & policy rules        [IMPLEMENTED — CP3]
│       │   ├── __init__.py     # Public rules surface
│       │   ├── codes.py        # RuleId, RuleCode, RuleStage — stable machine vocabulary
│       │   ├── results.py      # RuleStatus, RuleDetail, RuleResult, RuleEvaluation
│       │   ├── context.py      # RuleFact & frozen RuleContext (caller-supplied facts)
│       │   ├── base.py         # Abstract Rule contract
│       │   ├── registry.py     # Rule registry, four-way condition classification, CP6 gate set
│       │   ├── engine.py       # Rule execution pipeline (hybrid, deterministic order)
│       │   ├── authority.py    # Role & permission checks          — CP3: 1 rule
│       │   ├── dependencies.py # Plan & dependency checks          — CP3: 1 rule
│       │   ├── evidence.py     # Mandatory System/Worker evidence  — CP3: 1 rule
│       │   └── acceptance.py   # QA Final Pass & scoped defects    — CP3: 3 rules
│       │
│       ├── core/               # OS kernel & transactional coordinator        [PLANNED — CP6]
│       │   ├── __init__.py
│       │   ├── kernel.py       # Central OS Kernel coordinator
│       │   ├── transition.py   # Transactional state transition runner
│       │   └── context.py      # Execution & actor context
│       │
│       ├── events/             # Event model & notification bus               [PLANNED — CP5]
│       │   ├── __init__.py
│       │   ├── types.py        # Domain event schemas
│       │   ├── bus.py          # PostgreSQL LISTEN/NOTIFY bus
│       │   └── listener.py     # Async event listener runner
│       │
│       ├── storage/            # Persistence & data access
│       │   ├── __init__.py                                          [IMPLEMENTED — CP1]
│       │   ├── database.py     # SQLAlchemy engine & sessionmaker    [IMPLEMENTED — CP1]
│       │   ├── errors.py       # Persistence exception hierarchy     [PLANNED — CP4]
│       │   ├── unit_of_work.py # Session scope; owns no boundary     [PLANNED — CP4]
│       │   ├── models/         # SQLAlchemy ORM table definitions
│       │   │   ├── __init__.py # Declarative Base re-export          [IMPLEMENTED — CP1]
│       │   │   ├── actor.py                                         [PLANNED — CP4]
│       │   │   ├── feature.py                                       [PLANNED — CP4]
│       │   │   ├── plan.py                                          [PLANNED — CP4]
│       │   │   ├── task.py                                          [PLANNED — CP4]
│       │   │   ├── work_package.py                                  [PLANNED — CP4]
│       │   │   ├── evidence.py                                      [PLANNED — CP4]
│       │   │   ├── qa.py                                            [PLANNED — CP4]
│       │   │   ├── decision.py                                      [PLANNED — CP4]
│       │   │   └── event.py    # os_events, transitions audit        [PLANNED — CP5]
│       │   ├── mappers/        # Explicit domain <-> row translation [PLANNED — CP4]
│       │   │   ├── __init__.py
│       │   │   └── <one module per persisted entity>
│       │   └── repositories/   # Entity repositories & query helpers [PLANNED — CP4]
│       │       ├── __init__.py
│       │       ├── base.py     # Reusable mechanics only; no delete
│       │       ├── actor_repo.py
│       │       ├── feature_repo.py
│       │       ├── plan_repo.py
│       │       ├── task_repo.py
│       │       ├── task_revision_repo.py
│       │       ├── work_package_repo.py
│       │       ├── evidence_repo.py
│       │       ├── qa_repo.py
│       │       ├── review_decision_repo.py
│       │       ├── decision_repo.py
│       │       └── event_repo.py                                    [PLANNED — CP5]
│       │
│       ├── api/                # FastAPI HTTP REST control plane              [PLANNED — CP7]
│       │   ├── __init__.py
│       │   ├── dependencies.py # Actor context & DB session injection
│       │   ├── schemas/        # Request & response DTOs
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── features.py # Feature CRUD & Acceptance endpoints
│       │       ├── plans.py    # Feature Plan drafting & activation
│       │       ├── tasks.py    # Task assignment, start, transition
│       │       ├── submissions.py # Work package & evidence submissions
│       │       ├── reviews.py  # Reviewer decision endpoints
│       │       ├── qa.py       # QA report & finding submissions
│       │       └── decisions.py# Decision recording & acknowledgements
│       │
│       └── client/             # Typed Python SDK for agents & tools          [PLANNED — CP8]
│           ├── __init__.py
│           └── client.py
│
└── tests/
    ├── conftest.py             # Pytest fixtures, domain fixtures, test DB, async client  [IMPLEMENTED — CP1/CP2]
    ├── unit/
    │   ├── test_config.py             # Settings & environment          [IMPLEMENTED — CP1]
    │   ├── test_domain_models.py      # Domain invariants & validation  [IMPLEMENTED — CP2]
    │   ├── test_domain_immutability.py # Additive history & immutability [IMPLEMENTED — CP2]
    │   ├── test_domain_isolation.py   # Domain/state/rules purity       [IMPLEMENTED — CP2/CP3]
    │   ├── test_state_machines.py     # Lifecycle transitions & authority [IMPLEMENTED — CP2]
    │   ├── test_rule_engine.py     # Engine mechanics (stub rules)   [IMPLEMENTED — CP3]
    │   ├── test_rules.py           # The six CP3 rules               [IMPLEMENTED — CP3]
    │   ├── test_rule_invariants.py # Condition partition & CP6 gate  [IMPLEMENTED — CP3]
    │   └── _rule_io_probe.py       # Subprocess audit-hook I/O probe  [IMPLEMENTED — CP3]
    ├── integration/
    │   ├── test_health.py             # Application health endpoint     [IMPLEMENTED — CP1]
    │   ├── test_database.py           # PostgreSQL connectivity         [IMPLEMENTED — CP1]
    │   ├── test_migrations.py         # Alembic baseline migration      [IMPLEMENTED — CP1]
    │   ├── test_persistence.py                                         [PLANNED — CP4]
    │   ├── test_events_listen_notify.py                                [PLANNED — CP5]
    │   └── test_os_transition_enforcement.py                           [PLANNED — CP6]
    └── e2e/                                                            [PLANNED — CP8]
        └── test_first_vertical_slice.py
```

### Directory Rationale
- `src/ai_engineering_os/domain`: Kept isolated from I/O so domain rules and schemas are testable in microseconds without database mocks.
- `src/ai_engineering_os/state` & `rules`: Encapsulates OS deterministic behavior separate from web frameworks or ORMs. Both depend on `domain` only; **`rules` must not depend on `state`** (§3, ADR-004 4.7).
- `src/ai_engineering_os/storage`: Isolates all SQLAlchemy and relational mapping details. **ADR-005 5.11: ORM models never cross the repository boundary** — repositories return domain objects, and the Rule Engine and every higher layer must never receive a SQLAlchemy model. `mappers/` performs the translation explicitly; `errors.py` translates infrastructure failures (ADR-005 5.12); `unit_of_work.py` provides the session scope but owns no business transaction boundary (ADR-005 5.5).
- `src/ai_engineering_os/api`: Provides clean HTTP contract without business logic pollution.
- `tests/`: Separated into `unit`, `integration`, and `e2e` for fast local feedback loops.
- **Status markers:** The tree above distinguishes implemented code from the Foundation v1 target. **`[IMPLEMENTED]` markers are synchronized with the repository at the end of Checkpoint 3**; no Checkpoint 4 code exists yet. The `[PLANNED — CP4]` and `[PLANNED — CP5]` entries reflect the scope fixed by [ADR-005](../../adr/ADR-005.md). Markers must be re-synchronized as later checkpoints land.

---

## 12. Test Strategy

| Test Category | Target Scope | Key Verification Goals |
| :--- | :--- | :--- |
| **Domain Unit Tests** | `domain/`, `state/`, `rules/` | - Pydantic model validation and serialization.<br>- State machine valid vs. invalid transitions.<br>- Rule evaluators (evidence missing, role mismatch, unresolved blockers). |
| **Persistence Integration Tests** | `storage/` + PostgreSQL | - CRUD operations on relational models.<br>- Database transaction rollback on error.<br>- Immutability of revisions, and of **submitted** Work Package content (ADR-005 5.8).<br>- Alembic migrations up/down consistency. |
| **Event & Bus Integration Tests** | `events/` + PostgreSQL | - Events appended to `os_events` in sequential order.<br>- `LISTEN/NOTIFY` wakes asynchronous listeners reliably.<br>- Reconnection / state recovery from unhandled events. |
| **OS Enforcement Integration Tests** | `core/` + `rules/` + DB | - Worker cannot transition task to `SUBMITTED` without System Evidence.<br>- Coordinator cannot transition Feature to `ACCEPTED` without QA Final Pass.<br>- Unauthorized actor role transitions are deterministically blocked with 403/422. |
| **First Vertical Slice E2E Test** | `tests/e2e/test_first_vertical_slice.py` | Complete 11-step execution from Feature Creation to Final Acceptance, verifying state persistence, rule gating, event publication, and history reconstruction. |

---

## 13. Implementation Order

```
Checkpoint 1: Foundation Setup
              (pyproject.toml, Docker Compose, PostgreSQL, Alembic, Base Config)
     ↓
Checkpoint 2: Pure Domain Entities & State Machines
              (domain/, state/, Unit Tests)
     ↓
Checkpoint 3: Rule & Policy Engine
              (rules/, Evidence Rules, Authority Rules, Acceptance Rules)
     ↓
Checkpoint 4: Persistence & Storage Layer
              (SQLAlchemy models, Repositories, Alembic baseline migration)
     ↓
Checkpoint 5: Event Layer & LISTEN/NOTIFY Bus
              (os_events store, async notifier & subscriber loop)
     ↓
Checkpoint 6: OS Kernel & Transaction Runner
              (core/, atomic transaction wrapper, enforcement pipeline)
     ↓
Checkpoint 7: FastAPI Control Plane & Endpoints
              (api/ routers, dependencies, schemas)
     ↓
Checkpoint 8: Typed Client SDK & E2E Vertical Slice Test
              (client/, test_first_vertical_slice.py, full test suite pass)
```

---

## 14. Implementation Risks & Technical Open Questions

The following are genuine technical implementation questions for Foundation v1 (not architectural re-openings):

1. **Database Row-Level Locking vs Optimistic Locking — RESOLVED 2026-09-02 (ADR-005 5.6).**
   - *Question:* Should high-concurrency state transitions rely primarily on pessimistic locking (`SELECT FOR UPDATE`) or optimistic concurrency control with an integer version column (`version_id`)?
   - *Original recommendation for v1 — SUPERSEDED:* Use `SELECT FOR UPDATE` inside short database transactions.
   - *Ruling ([ADR-005](../../adr/ADR-005.md) 5.6):* **Optimistic locking.** Concurrent modification must be **detected and reported**, never silently overwritten. A version column exists on the authoritative-state tables only — `actors`, `features`, `feature_plans`, `tasks`, `work_packages` — because a row that is never updated cannot lose an update race. A conflict raises `ConcurrencyConflictError` and the caller decides the business response.
   - *Consequence:* The §7.2 conceptual snippet has been **rewritten** to depict version-checked commit rather than a pessimistic row lock; the Validation-First sequence it illustrates is unchanged. **No Checkpoint 2 domain model is modified**: the version is a property of the stored row, tracked inside the session and never exposed across the repository boundary (ADR-005 5.11).
2. **Evidence Storage & Payload Sizing Strategy:**
   - *Requirement:* The architecture strictly requires durable, retrievable, and integrity-verifiable evidence records.
   - *Implementation Strategy for v1:* The threshold for storing evidence inline in PostgreSQL (`TEXT`/`JSONB`) versus offloading to external/file storage is an initial implementation and configuration parameter (`MAX_INLINE_EVIDENCE_BYTES`, defaulting to 5MB) rather than an unchangeable architectural constraint. Payloads exceeding the configured threshold store a durable URI reference accompanied by an authoritative SHA-256 integrity checksum in PostgreSQL. This threshold can be adjusted based on operational benchmarks without changing the domain architecture.
3. **PostgreSQL LISTEN/NOTIFY Payload Limits:**
   - *Question:* PostgreSQL `NOTIFY` has an 8,000-byte payload limit.
   - *Recommendation for v1:* Never send full domain objects over `NOTIFY`. Send lightweight event envelopes containing only `{"event_id": "<uuid>", "aggregate_type": "Task", "aggregate_id": "<uuid>"}`. Receivers fetch the authoritative state directly from PostgreSQL.
4. **Local Development Authentication Strategy:**
   - *Question:* How should actor identities be passed during local development and testing?
   - *Recommendation for v1:* Use HTTP headers (`X-Actor-ID`, `X-Actor-Role`, `X-Domain-ID`) resolved via FastAPI dependency injection, with a configurable authentication middleware hook for future token-based auth.

### 14.1 Questions Carried Forward From ADR-003

The following were surfaced during Checkpoint 2. Item numbering is stable and is referenced from §4, §5, and §15. Items still marked UNRESOLVED or DEFERRED **must not be silently decided during implementation**.

5. **In-Scope Defect Identification — RESOLVED 2026-08-25 (ADR-003 3.11).**
   - *Problem (as recorded):* Design Session 009 gates Feature Acceptance on "zero unresolved **in-scope** defects", but `QADefect` (§4.1 #7) carries no in-scope marker, and `Feature.in_scope` is a free-text list a defect cannot be mechanically matched against.
   - *Ruling:* Scope is **derived by the OS from a validated structural association** (`Defect -> Task -> Feature`, or `Defect -> Feature`), never from a QA-supplied boolean. A scope-unresolved defect invalidates a QA Final Pass. The OS validates the relationship, not the judgement behind it. See §4.1 #7 and §5.1.
   - *Consequence:* `QAInScopeZeroDefectRule` (§15 Checkpoint 3) can now be written deterministically, and `QADefect` gains scope-association fields. **Implemented by ADR-004 4.8 (scope cardinality) and 4.10 (the `qa_in_scope_zero_defects` rule).**
6. **Escalation Blocking / `BLOCKED` State — DEFERRED. Must be designed explicitly before implementation.**
   - *Requirement:* Design Session 008 requires the OS to prevent affected Workers continuing knowingly invalid work after an Orchestrator decision, while preserving the current work.
   - *Status:* Deferred from Foundation v1 (ADR-003 3.3). Not implemented, and knowingly unserved in v1. Entry states, exit states, and initiating authority must all be designed before any implementation.
7. **Coordinator Lifecycle, Domain Registry, and Builder-Approval Registration — DEFERRED. Must be resolved before the Domain Registry is implemented.**
   - *Requirement:* Design Session 009 defines the Coordinator lifecycle (`PROPOSED -> APPROVED -> ACTIVE -> SUSPENDED -> RETIRED`), the authoritative Domain Registry, and a Builder-approval gate before a Coordinator becomes `ACTIVE`.
   - *Status:* Deferred from Foundation v1 (ADR-003 3.10), which uses `Actor.is_active` only. **This is an explicit deferral, not a rejection.** No `coordinators` or Domain Registry persistence may be created until it is resolved.
8. **Task Instantiation Timing — RESOLVED 2026-08-25 (ADR-003 3.12).**
   - *Problem (as recorded):* Design Session 007 states the Coordinator creates Tasks only when their dependencies are satisfied and that Tasks are not created speculatively. §5.1 requires Tasks to be instantiated at `PLANNED -> IN_PROGRESS`, with §5.2 providing `PENDING_DEPENDENCIES` to park them. These describe different instantiation timings.
   - *Ruling:* Tasks **may be created while the plan is `DRAFT`**; existence confers no execution authority. Authorization derives from the originating plan being `ACTIVE` and is enforced on `-> READY` (§5.2). Design Session 007's protection is preserved by the gate rather than by delaying creation. `Task` gains `feature_plan_id` and `plan_definition_key` (§4.1 #3). **ADR-004 4.8 performs that revisit at Checkpoint 3 start and makes both fields required; the `ORIGINATING_PLAN_ACTIVE` rule itself remains deferred (§5.2, §15 Checkpoint 3).**
9. **Post-Supersession Routing — RESOLVED IN PART 2026-08-25 (ADR-003 3.13). Residual UNRESOLVED; relevant to Checkpoint 6.**
   - *Problem (as recorded):* Design Session 009 does not state what happens to a Feature when its plan is superseded, or how the successor plan revision is instantiated.
   - *Ruling (Plan and Tasks):* The OS performs **no automatic routing** — no migration, no deletion, no halting. The Coordinator explicitly dispositions each unfinished Task (resume / reuse / abandon / redirect, Design Session 008). Not-yet-authorized Tasks simply remain unauthorized; in-flight Tasks are not interrupted, because Foundation v1 has no halt mechanism (item 6). See §5.4.
   - *Residual — UNRESOLVED:* what happens to the **Feature's own lifecycle status** when its plan is superseded, and how the successor plan revision is instantiated. ADR-003 3.13 explicitly does not decide this.
10. **QA Severity / Priority Taxonomy — DEFERRED.**
   - *Status:* Design Session 004 explicitly leaves the classification system open. `severity` and `priority` remain free-text labels (ADR-003 3.6). No taxonomy is required by Foundation v1.
11. **Task Stop / Abandon Lifecycle and Disposition Record — DEFERRED (ADR-003 D-6). Must be designed explicitly before any post-supersession disposition is implemented.**
   - *Requirement:* ADR-003 3.13 allows work that is no longer required to be "stopped according to the eventual lifecycle rules", and leaves the Coordinator's disposition decision unrecorded.
   - *Status:* The Task lifecycle (§5.2) defines **no** terminal state for stopped work, and no entity records a disposition decision or links a superseded plan's Task to successor planned work. Deferred from Foundation v1, not rejected. Relevant to Checkpoint 6.

### 14.2 Questions Carried Forward From ADR-004

Surfaced during the Checkpoint 3 planning review. Numbering continues §14.1 and is stable.

12. **`FRONTEND` and `QA` Mandatory System Evidence Standards — UNRESOLVED. Must not be invented during implementation.**
   - *Problem:* Design Session 005 defines Evidence Standards for the **Backend Worker only**. §4.1 #5 and §5.2 require mandatory System Evidence keyed by `Task.capability` (ADR-003 3.7), but no standard exists for `FRONTEND` or `QA`.
   - *Interim behaviour (ADR-004 4.9):* a capability with no approved standard **fails closed** with the stable code `EVIDENCE_STANDARD_UNDEFINED`. **An undefined standard is never treated as "no evidence required."** The code is deliberately distinct from `MISSING_SYSTEM_EVIDENCE` so a rejection never falsely blames the Worker for a gap in the OS.
   - *Status:* **UNRESOLVED.** Must be resolved before any Frontend or QA Task can be submitted. Not exercised by the Foundation v1 vertical slice, which uses a backend Worker.
13. **Deterministic Applicability for `DB_VERIFICATION` — UNRESOLVED. Must not be invented during implementation.**
   - *Problem:* Design Session 005 lists database verification as required for a Backend Worker "**when applicable**". Applicability is engineering judgement, which Design Session 005 assigns to the Reviewer at Stage 2 rather than to deterministic OS enforcement at Stage 1.
   - *Ruling (ADR-004 4.9):* `DB_VERIFICATION` is **not** part of the deterministic mandatory Checkpoint 3 evidence set. **No applicability logic is invented.**
   - *Status:* **UNRESOLVED.** No gate set. A deterministic applicability rule must be explicitly designed before `DB_VERIFICATION` may become mandatory.
14. **Foundation v1 Required Conditions & The Checkpoint 6 Gate — RESOLVED (ADR-004 4.12, 4.13).**
   - *Problem:* Checkpoint 3 implements six of the thirty-one declared transition conditions (§15 Checkpoint 3). Without a gate, the remaining Foundation v1-required conditions could be silently unenforced once the Kernel goes live.
   - *Ruling:* `FOUNDATION_V1_REQUIRED_CONDITIONS` is **derived from the `TransitionCondition` entries attached to the transitions the approved vertical slice (§10.2) walks** — **24 of 31**. No separate checklist is authored. Checkpoint 6 may not operate against Foundation v1 until every required condition is either implemented by a Rule or satisfied by a proven domain invariant (§15 Checkpoint 6).
   - *Consequence:* **All four `BLOCKED_CONDITIONS` are Foundation v1-required.** Items 15, 16, and 17 are therefore on the **critical path to Checkpoint 6**, not in a backlog.
15. **Definition of "Implementation Task" — BLOCKED. Must not be silently decided.**
   - *Problem:* §5.1 gates `IN_PROGRESS -> IN_VALIDATION` on `ALL_IMPLEMENTATION_TASKS_ACCEPTED`, but "implementation task" is undefined across Design Sessions 001–009, ADR-003, and this Blueprint. Inferring it from `capability != QA` would be inventing architecture.
   - *Status:* **UNRESOLVED.** Classified `BLOCKED_CONDITIONS` (ADR-004 4.11). Foundation v1-required; blocks Checkpoint 6.
16. **Feature-Level Mandatory Evidence Set — BLOCKED. Must not be silently decided.**
   - *Problem:* §5.1 gates `IN_VALIDATION -> ACCEPTED` on `MANDATORY_EVIDENCE_PRESENT`, and Design Session 009 requires "mandatory QA evidence present", but no Feature-level required evidence set is defined anywhere. Design Session 005's standards are per-Worker-type.
   - *Status:* **UNRESOLVED.** Classified `BLOCKED_CONDITIONS` (ADR-004 4.11). Foundation v1-required; blocks Checkpoint 6.
17. **Reviewer Assignment & Routing Model — BLOCKED. Must not be silently decided.**
   - *Problem:* §5.2 gates `SUBMITTED -> IN_REVIEW` on `REVIEWER_ASSIGNED` and describes "automatic routing to assigned Reviewer", but **no domain concept exists**: `Task` (§4.1 #3) carries no reviewer, and no routing or assignment model is defined.
   - *Status:* **UNRESOLVED.** Classified `BLOCKED_CONDITIONS` (ADR-004 4.11). Foundation v1-required; blocks Checkpoint 6.

### 14.3 Questions Carried Forward From The Checkpoint 3 Audit

Surfaced by the Checkpoint 3 implementation audit and ruled on by the Builder on 2026-08-29 ([ADR-004](../../adr/ADR-004.md) 4.14–4.16). Numbering continues §14.2 and is stable.

18. **Authoritative / Current QA-Result Selection Mechanism — UNRESOLVED. Must not be invented during implementation.**
   - *Problem:* `QAReport` is immutable (§7.1), so an `OPEN` defect recorded in a superseded report stays `OPEN` in that record forever. Treating all historical reports as live blockers makes any Feature that ever failed QA permanently unacceptable and renders the §5.1 `IN_VALIDATION -> IN_PROGRESS` rework loop unreachable. Nothing in the architecture identifies which QA Report states a Feature's **current** defect position.
   - *Ruling (ADR-004 4.15):* Historical QA Reports are **audit history, not standing vetoes**. **Selecting the authoritative result and evaluating it are separate concerns owned by separate components**: the Checkpoint 6 Kernel / context loader selects, and the rule layer evaluates whatever the `RuleContext` supplies, **taking no view on how many reports it receives**. **No recency ordering, sequence number, timestamp comparison, "latest" marker, `current_report_id`, QA session identity, persistence query, or additional `RuleContext` fact is introduced.**
   - *Status:* **UNRESOLVED. Must be designed before Checkpoint 6**, which owns the context loader that decides which QA Reports a rule sees.
   - *Known limitation:* until that mechanism exists, the correctness of `ZERO_UNRESOLVED_IN_SCOPE_DEFECTS` depends entirely on the caller supplying the right reports. Checkpoint 3 proves the ADR-003 3.11 **derivation**, not the end-to-end acceptance guarantee. **Recorded as a limitation, not claimed as enforcement.**
19. **Referential Validation Of A Feature Scope Association — UNRESOLVED. No gate set on Checkpoint 3.**
   - *Problem:* The seven-fact `RuleContext` (ADR-004 4.4) supplies only the Feature under acceptance, so an existing **different** Feature and a **nonexistent** Feature identifier are indistinguishable to a rule.
   - *Ruling (ADR-004 4.16):* **No `known_feature_ids` fact is added** and no lookup is invented. Both cases are treated as out of scope under ADR-004 4.14. A dangling **Task** association *is* detected, because the Task facts needed to check it are supplied; the asymmetry follows directly from the approved fact set.
   - *Status:* **RESOLVED IN PART 2026-09-02 (ADR-005 5.14). Residual belongs to Checkpoint 6.**
   - *Ruling ([ADR-005](../../adr/ADR-005.md) 5.14):* The persistence half is closed by construction. `qa_defects.scope_task_id` and `scope_feature_id` carry **referential foreign keys**, so a **nonexistent** identifier is unstorable. Both columns remain **nullable**, **both-null remains valid** as the unresolved-scope path, and both-set remains rejected (ADR-004 4.8). Only *unresolved* scope and *different-Feature* scope — out of scope and non-blocking per ADR-004 4.14 — remain representable.
   - *Unchanged:* **[ADR-004](../../adr/ADR-004.md) 4.16's ruling about the rule layer stands.** The seven-fact `RuleContext` gains nothing, **no `known_feature_ids` fact is added**, and the rule layer still makes no existence claim. **Checkpoint 3 does not claim to validate Feature-reference existence**, and Checkpoint 4 does not give it that ability — it removes the invalid data instead.
   - *Residual — relevant to Checkpoint 6:* whether the context loader should verify a Feature association against loaded facts remains a Checkpoint 6 design question. No gate is set.

---

## 15. Implementation Checkpoints

### Checkpoint 1: Project Environment & Tooling Baseline
- Configure `pyproject.toml` with dependencies (FastAPI, Pydantic v2, SQLAlchemy v2 async, asyncpg, Alembic, uvicorn, pytest, pytest-asyncio, ruff, mypy).
- Create `docker-compose.yml` defining PostgreSQL 16 service and test database.
- Configure `alembic.ini` and verify clean database connectivity.

### Checkpoint 2: Domain Entities, Enums & State Machines
- Implement pure domain models in `src/ai_engineering_os/domain/`.
- Implement state machine graphs and transition precondition evaluators in `src/ai_engineering_os/state/`.
- Write comprehensive unit tests verifying valid and invalid transitions.
- **[ADR-003](../../adr/ADR-003.md) is authoritative for the Foundation v1 domain-model and lifecycle clarifications discovered during this checkpoint.**
- **Checkpoint 2 revisit (ADR-003 3.11, 3.12) — performed IN FULL as Checkpoint 3 Phase 0 (ADR-004 4.8), not inside Checkpoint 2's completed record:**
  - `QADefect` gains its scope association (`scope_task_id` / `scope_feature_id`), with the cardinality rules of §4.1 #7: at most one may be set; **both-absent remains valid** and represents unresolved scope. OS-side scope resolution lives in the rule, not the model.
  - `Task` gains `feature_plan_id` and `plan_definition_key` (§4.1 #3). **Both are required** (ADR-004 4.8).
  - `TransitionCondition` relocates to the `domain` layer, with public re-exports preserved (§3, ADR-004 4.7).
  - `ORIGINATING_PLAN_ACTIVE` is added to the condition vocabulary and declared on **both** Task `-> READY` edges (§5.2).
  - **The `ORIGINATING_PLAN_ACTIVE` rule is NOT implemented here.** It remains deferred in `PENDING_RULE_EXPANSION`; enforcement sits with the Checkpoint 6 transition runner (ADR-003 3.12). This revisit records domain facts and state declarations required by already-approved decisions — **it is not permission to widen the Checkpoint 3 rule set.**

### Checkpoint 3: Rule & Policy Engine

**[ADR-004](../../adr/ADR-004.md) is authoritative for the Rule Engine architecture and the scope of this checkpoint.**

Checkpoint 3 builds the **generic Rule Engine foundation and proves it against a small number of real OS rules.** It is deliberately **not** the complete rule library.

**Phase 0 — Checkpoint 2 revisit, in full (ADR-004 4.8).** See §15 Checkpoint 2 above. Performed before any rule is written.

**Phase 1 — the generic engine** in `src/ai_engineering_os/rules/`:
- A single abstract `Rule` contract; rules are **explicit, strongly typed Python implementations** (ADR-004 4.1). **No JSON/YAML DSL, no configuration-driven rule language, no runtime expression evaluator, no LLM rule evaluation.**
- **Hybrid evaluation** (ADR-004 4.2): every rule whose declared prerequisites held is evaluated; **evaluation never stops at the first failure**; independent failures aggregate; a rule is skipped **only** because a prerequisite it explicitly declared failed or was skipped, and skips cascade transitively.
- **Deterministic, OS-owned ordering** (ADR-004 4.3): fixed stage order — 1 Actor/Authority, 2 State transition, 3 Plan/Dependencies, 4 Evidence, 5 Acceptance — with registry declaration order as the tie-break. **Agents never choose rule order; runtime configuration never reorders rules.** Stage 2 is declared and empty in Foundation v1.
- **Typed, frozen `RuleContext`** of caller-supplied facts (ADR-004 4.4). **No database, session, repository, filesystem, network, clock, or random source.** Each rule declares the facts it requires; a missing required fact **fails closed** with a structured error rather than passing silently.
- **Structured `RuleResult`** (ADR-004 4.5): stable `rule_id` and `code` vocabularies, human-readable `message`, typed ordered `details`, and statuses `PASSED` / `FAILED` / `SKIPPED`. **`NOT_APPLICABLE` is deliberately absent.** Aggregate evaluations additionally report conditions that were requested but have no registered rule.
- **Pure, read-only rules** (ADR-004 4.6): no mutation, no persistence, no audit records, no events, no external I/O. Mutation, transaction, audit, and event publication belong to the Checkpoint 6 Kernel.
- The **four-way condition classification** registry and the derived Checkpoint 6 gate set (ADR-004 4.11, 4.13).

**Phase 2 — exactly six representative rules (ADR-004 4.10).** No others are implemented in this checkpoint:

| Rule | Category | Condition | Edge |
| :--- | :--- | :--- | :--- |
| `worker_capability_matches` | Authority | `WORKER_CAPABILITY_MATCHES` | Task `READY -> ASSIGNED` |
| `dependencies_accepted` | Plan / dependency | `DEPENDENCIES_ACCEPTED` | Task `CREATED` / `PENDING_DEPENDENCIES -> READY` |
| `system_evidence_required` | Evidence | `MANDATORY_SYSTEM_EVIDENCE_ATTACHED` | Task `IN_PROGRESS -> SUBMITTED` |
| `all_tasks_accepted` | Acceptance | `ALL_TASKS_ACCEPTED` | Feature `IN_VALIDATION -> ACCEPTED` |
| `qa_final_pass_recorded` | Acceptance | `QA_FINAL_PASS_RECORDED` | Feature `IN_VALIDATION -> ACCEPTED` |
| `qa_in_scope_zero_defects` | Acceptance | `ZERO_UNRESOLVED_IN_SCOPE_DEFECTS` | Feature `IN_VALIDATION -> ACCEPTED` |

These six are the four rules originally named for this checkpoint (`AuthorityRule`, `SystemEvidenceRule`, `SequentialDependencyRule`, `QAInScopeZeroDefectRule`) plus the two acceptance rules that make hybrid evaluation demonstrable against real conditions. `qa_in_scope_zero_defects` declares `qa_final_pass_recorded` as its prerequisite; the other five are independent.

- **`system_evidence_required` must be keyed off `Task.capability` (ADR-003 3.7), not off `claim_type`.** Design Session 005 defines Evidence Standards per Worker type.
- **Evidence standards fail closed (ADR-004 4.9).** `BACKEND` requires `GIT_DIFF`, `TEST_OUTPUT`, and `API_RESPONSE`. **`FRONTEND` and `QA` standards are NOT invented**; a capability with no approved standard fails with the stable code `EVIDENCE_STANDARD_UNDEFINED`, never with an implicit pass. **`DB_VERIFICATION` is not in the deterministic mandatory set** and no applicability logic is invented (§14, items 12–13).
- **Precondition — CLEARED.** §14 item 5 (in-scope defect identification) is resolved by ADR-003 3.11.
- **`qa_in_scope_zero_defects` evaluates derived scope (ADR-003 3.11, as amended 2026-08-29).** It resolves each defect via `Defect -> Task -> Feature` (or `Defect -> Feature`) and counts only unresolved defects resolving to the Feature under acceptance. It **must never read a QA-supplied `in_scope` flag**, and it must reject a scope-unresolved defect, naming the defect in the rejection. **A defect resolving to a different Feature is out of scope and does not block** (ADR-004 4.14).
- **QA history is not a standing veto, and the rule does not police its own facts (ADR-004 4.15).** `qa_in_scope_zero_defects` evaluates the QA Reports supplied in the `RuleContext` and **takes no view on their cardinality**; repeat QA per Task Revision and per rework cycle is normal. **Selecting the authoritative QA result belongs to the Checkpoint 6 context loader. The authoritative / current QA-result mechanism is NOT designed at Checkpoint 3** and must not be invented (§14 item 18).
- **The seven-fact `RuleContext` is unchanged (ADR-004 4.16).** No `known_feature_ids` fact is added, so Checkpoint 3 **cannot** distinguish an existing different Feature from a nonexistent Feature identifier and does not claim to (§14 item 19).

**Phase 3 — tests.** Engine mechanics against stub rules; pass/fail/code/details coverage for all six rules; real-rule hybrid scenarios (independent aggregation, prerequisite skipping, unevaluated-condition reporting) and the full ADR-003 3.11 defect-scope matrix; architectural invariants proving `rules/` imports no SQLAlchemy, storage, repository, session, FastAPI, or network client, performs no runtime I/O, mutates nothing, and leaves **no `TransitionCondition` unaccounted for**.

**Explicit rule expansion boundary (ADR-004 4.11).** Remaining conditions are never silently implemented. Every vocabulary entry is classified into exactly one of four registry constants, which **partition** the vocabulary:

| Classification | Count at CP3 | Meaning |
| :--- | :--- | :--- |
| Implemented | 6 | A registered rule evaluates it today |
| `PENDING_RULE_EXPANSION` | 17 | Computable now; **not yet written** — a scope decision |
| `SATISFIED_BY_DOMAIN_INVARIANT` | 4 | Guaranteed by domain-model construction; enforcement discharged by pinning the guaranteeing validator instead of writing an unfalsifiable rule |
| `BLOCKED_CONDITIONS` | 4 | Cannot be written without a Builder ruling or later-checkpoint machinery (§14, items 15–17) — an **owed decision** |

**What Checkpoint 3 does NOT do.** No persistence, no events, no HTTP, no Kernel, no mutation, and **no context loader** — the component that reads facts from persistence into a `RuleContext` belongs to Checkpoint 6 on Checkpoint 4 repositories. It resolves no open question, invents no lifecycle state, and creates no authority. **D-1 (`BLOCKED`) and D-6 remain deferred and untouched.**

### Checkpoint 4: Database Persistence & Migrations

**[ADR-005](../../adr/ADR-005.md) is authoritative for the persistence architecture and the scope of this checkpoint.**

Checkpoint 4 builds the durable store and the repositories that Checkpoint 6 will read facts from. **It stores and retrieves. It evaluates no rule, validates no transition, and advances no state.**

- **Precondition:** §14 item 7 (Coordinator lifecycle) must be resolved before any `coordinators` or Domain Registry table is created. **Satisfied by ADR-005 5.1**, which creates a single `actors` table and no registry.
- **Constraint:** Append-only tables are insert-only (§7.1). `task_revisions` must have no mutable status column.
- **Constraint (ADR-003 3.12, ADR-004 4.8):** `tasks` carries the originating-plan columns (`feature_plan_id`, `plan_definition_key`), both **NOT NULL**; QA defect rows carry the scope-association columns (ADR-003 3.11), both nullable, with at most one populated per row and **both-null permitted** to represent unresolved scope.
- **Boundary (ADR-004 4.4).** The domain **fields** land at Checkpoint 3 Phase 0; their **columns** land here. Checkpoint 4 also owns the repositories that Checkpoint 6 will use to assemble a `RuleContext`; **Checkpoint 3 ships no context loader and no fact-fetching protocol**, so persistence never shapes the rule layer. **Checkpoint 4 ships no context loader either** — that component belongs to Checkpoint 6.
- **Constraint (ADR-003 3.13):** **No** automatic migration, reassignment, or deletion of a superseded plan's Tasks may be implemented in any repository or migration.

**Scope, per [ADR-005](../../adr/ADR-005.md):**

- **ORM models** for fourteen tables: `actors`, `features`, `feature_plans`, `plan_task_definitions`, `tasks`, `task_dependencies`, `task_revisions`, `work_packages`, `evidence_records`, `qa_reports`, `qa_defects`, `review_decisions`, `decisions`, `decision_acknowledgements` (ADR-005 5.1, 5.2, 5.8).
- **Explicit domain &harr; row mappers** (ADR-005 5.3, 5.11). Reconstruction runs every domain validator; a row that cannot form a valid domain object **fails** rather than being returned invalid or silently repaired.
- **A generic base repository plus domain-specific repositories** (ADR-005 5.4). The base carries reusable mechanics only; every domain query lives in its own repository. **No generic CRUD surface, and no `delete()` at all** (ADR-005 5.7).
- **A Unit of Work session scope** (ADR-005 5.5). Repositories use the supplied session and never commit. **The transaction owner is the Checkpoint 6 Kernel and is not built here**; integration tests stand in as the caller.
- **Optimistic-lock versions** on the five authoritative-state tables (ADR-005 5.6).
- **Persistence exception hierarchy** in `storage/errors.py` — `NotFoundError`, `ConcurrencyConflictError`, `PersistenceError` (ADR-005 5.12). **Not** added to `domain/errors.py`, whose recorded scope excludes persistence concerns.
- **Alembic migrations grouped by coherent schema change** (ADR-005 5.10). **`0001_baseline` is left untouched** — it has been applied wherever `tests/integration/test_migrations.py` has run, and an applied migration is immutable. New revisions follow it.
- **Database constraints for fundamental data integrity and evidence-based indexes** (ADR-005 5.14). Statuses are `VARCHAR` + `CHECK`, not native `ENUM`. **No deferred state — D-1 `BLOCKED` foremost — is added to any constraint.**
- **Persistence integration tests** and **architectural boundary tests**: no `rules` &harr; `storage` import in either direction, no ORM type crossing the repository boundary, no repository ordering or filtering by a persistence metadata timestamp, and the Checkpoint 3 suite still running **without a database**.

**What Checkpoint 4 does NOT do.** No Kernel, no transaction runner, and **no context loader** (Checkpoint 6). No service or use-case class owning a business transaction (Checkpoint 6). **No `os_events`, no `state_transitions_audit`, no event model, and no event repository** (Checkpoint 5, ADR-005 5.13). No HTTP layer (Checkpoint 7). **No new rule, transition condition, `RuleContext` fact, or lifecycle state.** No reviewer routing, QA authoritative-result selection, or Feature supersession lifecycle. **D-1 and D-6 remain deferred and untouched**, and no generic delete exists that could implement either by accident.

### Checkpoint 5: Event Store & Notification Bus
- **Scope correction (ADR-005 5.13):** this checkpoint owns **both** `os_events` **and** `state_transitions_audit` — their tables, models, migrations, and repositories. §11 previously marked the event model `[PLANNED — CP4]` and §15 Checkpoint 4 previously listed an `EventRepository`; **both are superseded.** `state_transitions_audit`, which no checkpoint previously owned, is assigned here.
- Implement `EventModel` and append-only event recording in `src/ai_engineering_os/events/`.
- Implement the `state_transitions_audit` record required by the §7.2 Validation-First invariant, so a rejected transition's durable audit entry has somewhere to land before the Checkpoint 6 runner needs it.
- Implement PostgreSQL `LISTEN/NOTIFY` emitter and async subscriber.
- Write integration tests for event persistence and notification wake-up.

### Checkpoint 6: OS Kernel & Transactional Transition Runner

> [!IMPORTANT]
> **BLOCKING PRECONDITION — Foundation v1 Rule Coverage Gate (ADR-004 4.12, 4.13).**
>
> **The OS Kernel MUST NOT become operational against Foundation v1 while any required Foundation v1 transition condition lacks enforcement.**
>
> ```
> Required Foundation v1 transition conditions
>               |
>    every required condition is either
>    implemented by a Rule, or satisfied
>    by a proven domain invariant
>               |
>         CP6 may proceed
> ```
>
> `FOUNDATION_V1_REQUIRED_CONDITIONS` is **derived from the `TransitionCondition` entries attached to the transitions the approved vertical slice (§10.2) walks** — **24 of the 31 vocabulary entries**. No separate, arbitrary checklist is authored; if the slice changes, the set is re-derived rather than edited by hand. The seven non-required entries are the rework and multi-task edges the slice does not walk; they remain part of the architecture and are not withdrawn.
>
> **The governing invariant:** *no Foundation v1-required condition may be silently unenforced when the Kernel goes live.*
>
> **Status at the end of Checkpoint 3:** 6 required conditions implemented, 2 satisfied by domain invariant, **16 outstanding** (12 in `PENDING_RULE_EXPANSION`, 4 in `BLOCKED_CONDITIONS`). **The gate is expected to fail at that point, by design.**
>
> **All four `BLOCKED_CONDITIONS` are Foundation v1-required**, so §14 items 15, 16, and 17 — the definition of "implementation task", the Feature-level mandatory evidence set, and the Reviewer assignment model — are on the **critical path to this checkpoint**. They must not be silently decided here.

- **Precondition — CLEARED.** §14 item 8 (Task instantiation timing) is resolved by ADR-003 3.12. The transition runner enforces the originating-plan-`ACTIVE` precondition on `-> READY` — implementing the `ORIGINATING_PLAN_ACTIVE` rule that Checkpoint 3 declared but deliberately deferred (§5.2, ADR-004 4.8) — and plan activation reconciles task definitions to Tasks (§5.4).
- **Separation of concerns (ADR-004 4.7).** The state machine answers *"is this transition structurally defined, and may this initiator request it?"*; the Rule Engine answers *"are the conditions this edge declares satisfied by these facts?"*; **only the Kernel mutates state, records audit, and publishes events.** The Kernel assembles the `RuleContext` from Checkpoint 4 repositories; the Rule Engine never loads its own facts.
- **Constraint (ADR-003 3.13):** On `ACTIVE -> SUPERSEDED` the runner performs **no** automatic Task migration, deletion, or halting. Disposition is Coordinator-initiated; its persisted record and any stop state are deferred (§14, item 11).
- **Open (§14, item 9):** the Feature-level consequence of supersession remains unresolved and must not be silently decided here.
- Implement `OSKernel` and `TransitionRunner` in `src/ai_engineering_os/core/`.
- Wire state machine checks, rule engine evaluations, database mutations, and event publications into single atomic transactions.
- Write integration tests verifying transition enforcement and rejection audit logging.

### Checkpoint 7: FastAPI Control Plane & Endpoints
- Implement FastAPI application, dependencies, and v1 routers (`features`, `tasks`, `submissions`, `reviews`, `qa`, `decisions`).
- Wire HTTP requests to OS Kernel commands.
- Verify automatic OpenAPI documentation and structured error responses.

### Checkpoint 8: Vertical Slice Integration Test & Review
- Implement lightweight Python `OSClient`.
- Implement `tests/e2e/test_first_vertical_slice.py` executing the complete 11-step lifecycle.
- Run complete test suite (`pytest`), linter (`ruff`), and type checker (`mypy`).
- Prepare Foundation v1 for Builder review.
