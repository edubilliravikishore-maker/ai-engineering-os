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
| `state` | Lifecycle state machines and transition graphs | Valid state graphs, transition definitions, state guards | Database sessions, HTTP handlers, agent prompting | `domain` |
| `rules` | Deterministic policy and transition rule validation | Rule evaluator interfaces, evidence validators, authority checkers | State mutation, DB connection management | `domain` |
| `core` | OS Kernel execution and orchestration | Transaction runner, command handlers, enforcement pipeline | Raw SQL queries, HTTP request parsing, agent generation | `domain`, `state`, `rules`, `events`, `storage` (interfaces) |
| `events` | Event definitions, event store, and notification bus | Event models, event serializer, Postgres LISTEN/NOTIFY publisher/listener | Domain business rules, HTTP endpoint logic | `domain`, `storage` |
| `storage` | Relational persistence and migrations | SQLAlchemy models, repositories, session management, Alembic migrations | Domain logic, agent execution, API schemas | `domain`, SQLAlchemy, Alembic |
| `api` | HTTP REST control plane | FastAPI routers, request/response schemas, auth/role extraction | Direct business logic, direct DB transactions (calls Kernel) | `core`, `domain`, FastAPI, Pydantic |
| `client` | Provider-agnostic SDK for agents and tools | Typed HTTP client, request formatters, response parsers | OS internal state machine execution | `domain`, httpx / requests |

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

#### 1. Feature
- **Identity:** `id` (UUID), `slug` (string), `title` (string).
- **Core Attributes:** `goal` (text), `requirements` (structured list), `in_scope` (list), `out_of_scope` (list), `acceptance_criteria` (list of testable assertions), `status` (`FeatureStatus`), `coordinator_id` (UUID), `created_at`, `updated_at`.
- **Relationship:** Belongs to one Coordinator; owns 1..* Feature Plans and 1..* Tasks.

#### 2. Feature Plan
- **Identity:** `id` (UUID), `feature_id` (UUID), `revision_number` (int).
- **Core Attributes:** `status` (`PlanStatus`), `required_capabilities` (list, e.g., `["backend", "frontend", "qa"]`), `task_definitions` (list of planned task specs with dependency graphs), `created_by` (UUID), `created_at`.
- **Relationship:** Belongs to one Feature; defines planned Tasks.

#### 3. Task
- **Identity:** `id` (UUID), `feature_id` (UUID), `title` (string).
- **Core Attributes:** `capability` (`CapabilityType`: `BACKEND`, `FRONTEND`, `QA`, etc.), `status` (`TaskStatus`), `assigned_worker_id` (UUID, optional), `dependencies` (list of prerequisite Task UUIDs), `active_revision_number` (int), `created_at`, `updated_at`.
- **Relationship:** Belongs to one Feature; owns 1..* Task Revisions.

#### 4. Task Revision
- **Identity:** `id` (UUID), `task_id` (UUID), `revision_number` (int).
- **Core Attributes:** `status` (`RevisionStatus`), `created_by_worker_id` (UUID), `work_package_id` (UUID, optional), `review_decision_id` (UUID, optional), `qa_report_id` (UUID, optional), `created_at`.
- **Invariant:** Strictly additive. History is never overwritten.

#### 5. Work Package
- **Identity:** `id` (UUID), `task_revision_id` (UUID).
- **Core Attributes:** `summary` (string), `claims` (list of `Claim` objects: `id`, `claim_type`, `description`), `verification_guide` (structured instructions, endpoints, expected outputs), `worker_notes` (design decisions, assumptions), `risks` (optional text), `submitted_at`.
- **Invariant:** Immutable once submitted.

#### 6. Evidence Record
- **Identity:** `id` (UUID), `work_package_id` (UUID, optional), `qa_report_id` (UUID, optional).
- **Core Attributes:** `source_type` (`SYSTEM` vs `WORKER`), `evidence_type` (`GIT_DIFF`, `TEST_OUTPUT`, `API_RESPONSE`, `BUILD_LOG`, `DB_VERIFICATION`, `REASONING`), `content` (text, JSON structure, or URI reference), `checksum` (e.g., SHA-256 for integrity verification), `metadata` (command, exit_code, git_hash, timestamp), `verified_by_os` (bool), `created_at`.
- **Invariants:** 
  - Evidence must be durable, retrievable, and integrity-verifiable.
  - System Evidence is generated independently and carries highest trust.
  - Evidence content storage (inline in PostgreSQL vs. referenced storage) is governed by a configurable size threshold (`MAX_INLINE_EVIDENCE_BYTES`) rather than a fixed architectural constraint.

#### 7. QA Report & QA Defect
- **Identity:** `id` (UUID), `feature_id` (UUID), `task_revision_id` (UUID, optional).
- **Core Attributes:** `is_final_pass` (bool), `tested_scope` (list), `results` (list of test results), `defects` (list of `QADefect`: `id`, `title`, `severity`, `priority`, `is_blocker`, `status`), `evidence_ids` (list of Evidence UUIDs), `status` (`QAStatus`: `PASSED`, `FAILED`, `BLOCKED`), `created_at`.

#### 8. Decision & Decision Acknowledgement
- **Identity:** `id` (UUID), `scope` (`DECISION_SCOPE`: `FEATURE`, `SYSTEM`, `BUSINESS`).
- **Core Attributes:** `decided_by_role` (`ActorRole`), `decided_by_id` (UUID), `problem` (text), `decision_text` (text), `reasoning` (text), `alternatives_considered` (list), `affected_domains` (list), `created_at`.
- **Acknowledgements:** `acknowledgements` (list of `DecisionAcknowledgement`: `actor_id`, `actor_role`, `acknowledged_at`).

#### 9. Actor & Agent
- **Identity:** `id` (UUID), `role` (`ActorRole`: `BUILDER`, `ORCHESTRATOR`, `COORDINATOR`, `WORKER`, `REVIEWER`, `QA`), `domain` (optional string), `name` (string), `is_active` (bool).

#### 10. Event & State Transition Audit Record
- **Event:** `id` (UUID), `event_type` (string), `aggregate_type` (string), `aggregate_id` (UUID), `actor_id` (UUID), `actor_role` (string), `payload` (JSONB), `occurred_at`.
- **State Transition Audit:** `id` (UUID), `entity_type` (string), `entity_id` (UUID), `from_state` (string), `to_state` (string), `requested_by` (UUID), `decision` (`ALLOWED` vs `REJECTED`), `rejection_reasons` (list of strings), `timestamp`.

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
| `PLANNED` | `IN_PROGRESS` | `COORDINATOR` | Plan is in `READY` status; tasks are instantiated in OS. | Plan is incomplete or invalid dependencies exist. |
| `IN_PROGRESS` | `IN_VALIDATION` | `COORDINATOR` / `OS` | All implementation tasks have reached `ACCEPTED` status from Reviewer. | Any implementation task is still in progress or rejected. |
| `IN_VALIDATION` | `ACCEPTED` | `COORDINATOR` | 1. All tasks completed.<br>2. Valid `QA Final Pass` exists.<br>3. Zero unresolved in-scope defects.<br>4. Mandatory evidence attached. | Missing QA Final Pass, unresolved blocker, or incomplete task. |
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
| `CREATED` / `PENDING_` | `READY` | `OS` | All declared prerequisite task IDs are in `ACCEPTED` state. | Prerequisite task is not `ACCEPTED`. |
| `READY` | `ASSIGNED` | `COORDINATOR` | Worker ID is active and possesses matching capability. | Worker inactive, nonexistent, or wrong capability. |
| `ASSIGNED` | `IN_PROGRESS` | `WORKER` | Requester matches `assigned_worker_id`. | Requester is not assigned worker. |
| `IN_PROGRESS` | `SUBMITTED` | `WORKER` | 1. Work Package present.<br>2. Claims defined.<br>3. Mandatory System Evidence attached.<br>4. Verification guide present. | Missing System Evidence, empty claims, or missing verification guide. |
| `SUBMITTED` | `IN_REVIEW` | `OS` | Automatic routing to assigned Reviewer. | Reviewer unavailable or unassigned. |
| `IN_REVIEW` | `IN_QA` | `REVIEWER` | Reviewer decision is `APPROVED` with review notes. | Missing review decision or unapproved status. |
| `IN_REVIEW` | `REVISION_REQUIRED` | `REVIEWER` | Reviewer decision is `CHANGES_REQUESTED` with explicit feedback. | Missing feedback rationale. |
| `IN_QA` | `ACCEPTED` | `QA` | QA Report records `PASSED` with test execution evidence. | Unresolved defects or missing test evidence. |
| `IN_QA` | `REVISION_REQUIRED` | `QA` / `COORDINATOR` | QA Report records `FAILED` with defect list. | Missing defect descriptions or severity ratings. |
| `REVISION_REQUIRED` | `IN_PROGRESS` | `WORKER` | Worker creates incremented Task Revision (`revision_number + 1`). | Attempting to overwrite existing revision. |

---

### 5.3 Work Package Lifecycle
- **States:** `DRAFT` (Worker local) $\rightarrow$ `SUBMITTED` (OS System of Record) $\rightarrow$ `VALIDATED` $\rightarrow$ `REVIEWED` $\rightarrow$ `ACCEPTED` / `REJECTED`.
- **Invariants:** 
  - A Work Package in `SUBMITTED` status is **immutable**.
  - No actor (including Worker, Reviewer, or Coordinator) can edit a submitted Work Package.
  - Fixes require generating a new Revision and a new Work Package entity.

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
| `FeaturePlanActivated`| Coordinator | OS / Workers | Yes (`IN_PROGRESS`) | Workers | Plan activated; dependency-free tasks move to `READY`. |
| `TaskAssigned` | Coordinator | Worker | Yes (`ASSIGNED`) | Assigned Worker | Task assigned to specific technical worker. |
| `TaskStarted` | Worker | OS / Coordinator | Yes (`IN_PROGRESS`) | Coordinator | Worker acknowledges and begins exploration/coding. |
| `WorkPackageSubmitted`| Worker | OS / Reviewer | Yes (`SUBMITTED`) | OS / Reviewer | Worker submits completed revision and evidence. |
| `EvidenceAttached` | Worker / OS / QA | OS | No | None | System/Worker evidence record bound to revision. |
| `StateTransitionAllowed`| OS Kernel | Interested Actors | Yes | Matching Actor | Audit record of successful lifecycle transition. |
| `StateTransitionRejected`| OS Kernel | Requesting Actor | No | Requesting Actor | Audit record of failed transition with failure reasons. |
| `ReviewCompleted` | Reviewer | Coordinator / Worker | Yes (`IN_QA` or `REVISION_REQ`) | Coordinator / Worker | Reviewer outcome (`APPROVED` vs `CHANGES_REQUESTED`). |
| `QAReportSubmitted` | QA | Coordinator / Worker | Yes (`ACCEPTED` or `REVISION_REQ`) | Coordinator / Worker | QA verification results, test runs, and defect list. |
| `FeatureAccepted` | Coordinator | Orchestrator / Builder | Yes (`ACCEPTED`) | Orchestrator / Builder | Feature delivery accepted by Coordinator. |
| `EscalationRaised` | Worker / Coordinator | Higher Authority | Yes (`BLOCKED`) | Orchestrator / Builder | Authority boundary reached; decision requested. |

---

## 7. Persistence Architecture (PostgreSQL)

### 7.1 Authoritative State vs Append-Only History

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           PostgreSQL Database                            │
│                                                                          │
│   AUTHORITATIVE CURRENT STATE                  APPEND-ONLY HISTORY       │
│  ┌─────────────────────────────┐              ┌────────────────────────┐ │
│  │ features                    │              │ os_events              │ │
│  │ tasks                       │              │ state_transitions_audit│ │
│  │ coordinators                │              │ task_revisions         │ │
│  │ workers                     │              │ work_packages          │ │
│  │ feature_plans               │              │ evidence_records       │ │
│  └─────────────────────────────┘              │ qa_reports / defects   │ │
│                                               │ decisions              │ │
│                                               └────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

1. **Authoritative State:** Relational tables holding the current, active status and relationships of living entities (`features.status`, `tasks.status`, `tasks.assigned_worker_id`).
2. **Append-Only History:** Immutable records capturing the exact sequence of engineering actions, revisions, evidence, and audit decisions.

### 7.2 Transactional Transition Boundary & Invariant
All OS state transitions are protected by explicit PostgreSQL ACID transactions.

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
# Conceptual Transactional Pattern in OS Kernel (Validation-First)
async with db.transaction() as session:
    # 1. Acquire row lock on target entity
    task = await session.get_for_update(TaskModel, task_id)
    
    # 2. Evaluate State Machine & Rule Engine BEFORE any mutation
    validation_result = rule_engine.validate_transition(
        task=task,
        target_state=TaskStatus.SUBMITTED,
        payload=work_package_payload,
        actor=current_actor
    )
    
    if not validation_result.is_valid:
        # State remains unchanged in task.status (IN_PROGRESS)
        # Durably record the rejection audit record and event in this committed transaction
        await session.record_rejection(
            entity_type="Task",
            entity_id=task.id,
            from_state=task.status,
            attempted_state=TaskStatus.SUBMITTED,
            actor=current_actor,
            reasons=validation_result.errors
        )
        await session.commit()
        raise TransitionRejectedException(errors=validation_result.errors)
    
    # 3. Apply state mutation ONLY after validation passes
    task.status = TaskStatus.SUBMITTED
    
    # 4. Insert immutable child records (Work Package, Evidence, Revision)
    revision = TaskRevisionModel(...)
    session.add(revision)
    
    # 5. Insert event into os_events
    event = EventModel(
        event_type="WorkPackageSubmitted",
        aggregate_type="Task",
        aggregate_id=task.id,
        payload=validation_result.event_payload
    )
    session.add(event)
    
    # 6. Commit transaction (PostgreSQL guarantees ACID durability)
    await session.commit()

# 7. Post-commit notification (LISTEN/NOTIFY)
await notification_bus.emit(channel="task_events", payload={"event_id": event.id})
```

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
        Coordinator drafts Feature Plan with Task 1: "Implement Auth API".
        Plan activated -> Task 1 created in READY status.

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

```
AI-Engineering-OS/
├── .gitignore
├── README.md
├── pyproject.toml              # Build config, dependencies, ruff, mypy, pytest
├── alembic.ini                 # Database migration config
├── docker-compose.yml          # Local PostgreSQL + OS runtime
├── Dockerfile                  # OS application container
│
├── adr/                        # Architecture Decision Records
├── brain/                      # Working memory & developer resources
├── design-sessions/            # Frozen architecture design sessions
├── docs/                       # Permanent project documentation
│   ├── 00-vision/
│   ├── 01-architecture/
│   └── 02-implementation/
│       └── Implementation-Blueprint.md
│
├── migrations/                 # Alembic migration versions
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── src/
│   └── ai_engineering_os/
│       ├── __init__.py
│       ├── main.py             # FastAPI entrypoint
│       ├── config.py           # Environment & OS settings
│       │
│       ├── domain/             # Pure domain entities, value objects, enums
│       │   ├── __init__.py
│       │   ├── enums.py        # Statuses, Roles, Capabilities, EvidenceTypes
│       │   ├── feature.py      # Feature & Scope models
│       │   ├── plan.py         # FeaturePlan & TaskDefinition models
│       │   ├── task.py         # Task & TaskRevision models
│       │   ├── work_package.py # WorkPackage & Claim models
│       │   ├── evidence.py     # EvidenceRecord models
│       │   ├── qa.py           # QAReport & QADefect models
│       │   └── decision.py     # Decision & Acknowledgement models
│       │
│       ├── state/              # State machines & transition definitions
│       │   ├── __init__.py
│       │   ├── machine.py      # Base state machine evaluator
│       │   ├── feature_sm.py   # Feature lifecycle graph & guards
│       │   ├── task_sm.py      # Task lifecycle graph & guards
│       │   └── plan_sm.py      # Plan lifecycle graph & guards
│       │
│       ├── rules/              # Rule validation engine & policy rules
│       │   ├── __init__.py
│       │   ├── engine.py       # Rule execution pipeline
│       │   ├── base.py         # Abstract rule class
│       │   ├── authority.py    # Role & permission checks
│       │   ├── evidence.py     # Mandatory System/Worker evidence checks
│       │   └── acceptance.py   # QA Final Pass & blocker checks
│       │
│       ├── core/               # OS kernel & transactional coordinator
│       │   ├── __init__.py
│       │   ├── kernel.py       # Central OS Kernel coordinator
│       │   ├── transition.py   # Transactional state transition runner
│       │   └── context.py      # Execution & actor context
│       │
│       ├── events/             # Event model & notification bus
│       │   ├── __init__.py
│       │   ├── types.py        # Domain event schemas
│       │   ├── bus.py          # PostgreSQL LISTEN/NOTIFY bus
│       │   └── listener.py     # Async event listener runner
│       │
│       ├── storage/            # Persistence & data access
│       │   ├── __init__.py
│       │   ├── database.py     # SQLAlchemy engine & sessionmaker
│       │   ├── models/         # SQLAlchemy ORM table definitions
│       │   │   ├── __init__.py
│       │   │   ├── feature.py
│       │   │   ├── task.py
│       │   │   ├── work_package.py
│       │   │   ├── evidence.py
│       │   │   ├── qa.py
│       │   │   ├── decision.py
│       │   │   └── event.py
│       │   └── repositories/   # Entity repositories & query helpers
│       │       ├── __init__.py
│       │       ├── feature_repo.py
│       │       ├── task_repo.py
│       │       └── event_repo.py
│       │
│       ├── api/                # FastAPI HTTP REST control plane
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
│       └── client/             # Typed Python SDK for agents & tools
│           ├── __init__.py
│           └── client.py
│
└── tests/
    ├── conftest.py             # Pytest fixtures, test DB, async client
    ├── unit/
    │   ├── test_domain_models.py
    │   ├── test_state_machines.py
    │   └── test_rule_engine.py
    ├── integration/
    │   ├── test_persistence.py
    │   ├── test_events_listen_notify.py
    │   └── test_os_transition_enforcement.py
    └── e2e/
        └── test_first_vertical_slice.py
```

### Directory Rationale
- `src/ai_engineering_os/domain`: Kept isolated from I/O so domain rules and schemas are testable in microseconds without database mocks.
- `src/ai_engineering_os/state` & `rules`: Encapsulates OS deterministic behavior separate from web frameworks or ORMs.
- `src/ai_engineering_os/storage`: Isolates all SQLAlchemy and relational mapping details.
- `src/ai_engineering_os/api`: Provides clean HTTP contract without business logic pollution.
- `tests/`: Separated into `unit`, `integration`, and `e2e` for fast local feedback loops.

---

## 12. Test Strategy

| Test Category | Target Scope | Key Verification Goals |
| :--- | :--- | :--- |
| **Domain Unit Tests** | `domain/`, `state/`, `rules/` | - Pydantic model validation and serialization.<br>- State machine valid vs. invalid transitions.<br>- Rule evaluators (evidence missing, role mismatch, unresolved blockers). |
| **Persistence Integration Tests** | `storage/` + PostgreSQL | - CRUD operations on relational models.<br>- Database transaction rollback on error.<br>- Immutability of revisions and Work Packages.<br>- Alembic migrations up/down consistency. |
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

1. **Database Row-Level Locking vs Optimistic Locking:**
   - *Question:* Should high-concurrency state transitions rely primarily on pessimistic locking (`SELECT FOR UPDATE`) or optimistic concurrency control with an integer version column (`version_id`)?
   - *Recommendation for v1:* Use `SELECT FOR UPDATE` inside short database transactions. It is deterministic, robust for low-to-medium initial concurrency, and avoids retry storms.
2. **Evidence Storage & Payload Sizing Strategy:**
   - *Requirement:* The architecture strictly requires durable, retrievable, and integrity-verifiable evidence records.
   - *Implementation Strategy for v1:* The threshold for storing evidence inline in PostgreSQL (`TEXT`/`JSONB`) versus offloading to external/file storage is an initial implementation and configuration parameter (`MAX_INLINE_EVIDENCE_BYTES`, defaulting to 5MB) rather than an unchangeable architectural constraint. Payloads exceeding the configured threshold store a durable URI reference accompanied by an authoritative SHA-256 integrity checksum in PostgreSQL. This threshold can be adjusted based on operational benchmarks without changing the domain architecture.
3. **PostgreSQL LISTEN/NOTIFY Payload Limits:**
   - *Question:* PostgreSQL `NOTIFY` has an 8,000-byte payload limit.
   - *Recommendation for v1:* Never send full domain objects over `NOTIFY`. Send lightweight event envelopes containing only `{"event_id": "<uuid>", "aggregate_type": "Task", "aggregate_id": "<uuid>"}`. Receivers fetch the authoritative state directly from PostgreSQL.
4. **Local Development Authentication Strategy:**
   - *Question:* How should actor identities be passed during local development and testing?
   - *Recommendation for v1:* Use HTTP headers (`X-Actor-ID`, `X-Actor-Role`, `X-Domain-ID`) resolved via FastAPI dependency injection, with a configurable authentication middleware hook for future token-based auth.

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

### Checkpoint 3: Rule & Policy Engine
- Implement `RuleEngine` and composable rule evaluators in `src/ai_engineering_os/rules/`.
- Implement `AuthorityRule`, `SystemEvidenceRule`, `SequentialDependencyRule`, and `QAInScopeZeroDefectRule`.
- Write unit tests verifying rule evaluation failures and success messages.

### Checkpoint 4: Database Persistence & Migrations
- Implement SQLAlchemy ORM models in `src/ai_engineering_os/storage/models/`.
- Generate and apply baseline Alembic migration script.
- Implement repository classes (`FeatureRepository`, `TaskRepository`, `EventRepository`).
- Write persistence integration tests.

### Checkpoint 5: Event Store & Notification Bus
- Implement `EventModel` and append-only event recording in `src/ai_engineering_os/events/`.
- Implement PostgreSQL `LISTEN/NOTIFY` emitter and async subscriber.
- Write integration tests for event persistence and notification wake-up.

### Checkpoint 6: OS Kernel & Transactional Transition Runner
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
