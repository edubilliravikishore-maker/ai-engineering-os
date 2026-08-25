"""Pytest test configuration and fixtures for AI Engineering OS.

Domain fixtures build valid baseline entities so individual unit tests can focus
on the specific invariant or transition under test.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from ai_engineering_os.config import Settings, get_settings
from ai_engineering_os.domain import (
    Actor,
    ActorId,
    ActorRole,
    CapabilityType,
    Claim,
    ClaimId,
    EvidenceId,
    EvidenceRecord,
    EvidenceSourceType,
    EvidenceType,
    Feature,
    FeatureId,
    FeaturePlan,
    FeaturePlanId,
    Task,
    TaskDefinition,
    TaskId,
    TaskRevision,
    TaskRevisionId,
    VerificationGuide,
    WorkPackage,
    WorkPackageId,
    new_id,
)
from ai_engineering_os.main import app
from ai_engineering_os.storage.database import close_database_connection


@pytest.fixture
def test_settings() -> Settings:
    """Provides application settings for test runs."""
    return get_settings()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient]:
    """Provides an asynchronous HTTP test client for the FastAPI application."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture(autouse=True)
async def cleanup_database_pool() -> AsyncGenerator[None]:
    """Cleans up database connection pool after each test."""
    yield
    await close_database_connection()


@pytest.fixture
def coordinator_id() -> ActorId:
    """Identity of the Coordinator owning the fixture Feature."""
    return new_id(ActorId)


@pytest.fixture
def worker_id() -> ActorId:
    """Identity of the Worker owning the fixture Task."""
    return new_id(ActorId)


@pytest.fixture
def backend_worker(worker_id: ActorId) -> Actor:
    """An active backend Worker."""
    return Actor(
        id=worker_id,
        role=ActorRole.WORKER,
        name="backend-worker-1",
        domain="auth-domain",
        capabilities=frozenset({CapabilityType.BACKEND}),
    )


@pytest.fixture
def feature(coordinator_id: ActorId) -> Feature:
    """A DRAFT Feature with a recorded scope boundary."""
    return Feature(
        id=new_id(FeatureId),
        slug="user-authentication",
        title="User Authentication via Email/Password",
        goal="Allow users to sign in with an email address and password",
        coordinator_id=coordinator_id,
        requirements=("Email/password login",),
        in_scope=("Email/password login", "Forgot password reset flow"),
        out_of_scope=("Google OAuth", "Phone OTP"),
        acceptance_criteria=("A valid credential pair returns an authenticated session",),
    )


@pytest.fixture
def feature_plan(feature: Feature, coordinator_id: ActorId) -> FeaturePlan:
    """A DRAFT Feature Plan with a two-node dependency graph."""
    return FeaturePlan(
        id=new_id(FeaturePlanId),
        feature_id=feature.id,
        revision_number=1,
        created_by=coordinator_id,
        required_capabilities=(CapabilityType.BACKEND, CapabilityType.QA),
        task_definitions=(
            TaskDefinition(
                key="auth-api", title="Implement Auth API", capability=CapabilityType.BACKEND
            ),
            TaskDefinition(
                key="auth-qa",
                title="Validate Auth API",
                capability=CapabilityType.QA,
                depends_on=("auth-api",),
            ),
        ),
    )


@pytest.fixture
def task(feature: Feature) -> Task:
    """A newly created Task with no dependencies."""
    return Task(
        id=new_id(TaskId),
        feature_id=feature.id,
        title="Implement Auth API",
        capability=CapabilityType.BACKEND,
    )


@pytest.fixture
def task_revision(task: Task, worker_id: ActorId) -> TaskRevision:
    """The first Revision of the fixture Task."""
    return TaskRevision(
        id=new_id(TaskRevisionId),
        task_id=task.id,
        revision_number=1,
        created_by_worker_id=worker_id,
    )


@pytest.fixture
def claim() -> Claim:
    """A single Work Package Claim."""
    return Claim(
        id=new_id(ClaimId), claim_type="API_IMPLEMENTED", description="Login API implemented"
    )


@pytest.fixture
def verification_guide() -> VerificationGuide:
    """A minimal Verification Guide."""
    return VerificationGuide(
        steps=("POST /auth/login with valid credentials",),
        endpoints=("POST /auth/login",),
        expected_outputs=("200 OK with a session token",),
    )


@pytest.fixture
def draft_work_package(task_revision: TaskRevision) -> WorkPackage:
    """A Worker-local DRAFT Work Package."""
    return WorkPackage(
        id=new_id(WorkPackageId),
        task_revision_id=task_revision.id,
        summary="Implemented the email/password login endpoint",
    )


@pytest.fixture
def system_evidence(draft_work_package: WorkPackage) -> EvidenceRecord:
    """Independently generated System Evidence bound to the fixture Work Package."""
    return EvidenceRecord.for_inline_content(
        id=new_id(EvidenceId),
        source_type=EvidenceSourceType.SYSTEM,
        evidence_type=EvidenceType.GIT_DIFF,
        content="diff --git a/auth.py b/auth.py",
        work_package_id=draft_work_package.id,
        verified_by_os=True,
    )
