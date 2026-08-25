"""Verifies the domain and state layers stay pure.

The blueprint requires that ``domain`` depends on nothing but Pydantic and the
standard library, and that ``state`` depends only on ``domain``. No domain model
may require FastAPI, SQLAlchemy, or PostgreSQL to operate.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ai_engineering_os.domain import Feature, Task

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "ai_engineering_os"
DOMAIN_ROOT = SOURCE_ROOT / "domain"
STATE_ROOT = SOURCE_ROOT / "state"

FORBIDDEN_PACKAGES = frozenset(
    {
        "alembic",
        "asyncpg",
        "fastapi",
        "httpx",
        "pathlib",
        "psycopg",
        "psycopg2",
        "requests",
        "socket",
        "sqlalchemy",
        "starlette",
        "urllib",
    }
)
"""Framework, database, network, and filesystem packages the pure layers must avoid."""


def _module_files(root: Path) -> list[Path]:
    return sorted(root.glob("*.py"))


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("module", _module_files(DOMAIN_ROOT), ids=lambda p: p.name)
def test_domain_module_has_no_infrastructure_dependency(module: Path) -> None:
    """Verifies no domain module imports a framework, database, or I/O package."""
    forbidden = sorted(_imported_roots(module) & FORBIDDEN_PACKAGES)
    assert not forbidden, f"{module.name} imports {forbidden}"


@pytest.mark.parametrize("module", _module_files(STATE_ROOT), ids=lambda p: p.name)
def test_state_module_has_no_infrastructure_dependency(module: Path) -> None:
    """Verifies no state module imports a framework, database, or I/O package."""
    forbidden = sorted(_imported_roots(module) & FORBIDDEN_PACKAGES)
    assert not forbidden, f"{module.name} imports {forbidden}"


@pytest.mark.parametrize("module", _module_files(STATE_ROOT), ids=lambda p: p.name)
def test_state_layer_only_depends_on_the_domain_layer(module: Path) -> None:
    """Verifies the state layer never reaches into storage, api, core, or events."""
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    internal = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and node.module.startswith("ai_engineering_os.")
    }
    illegal = sorted(
        name
        for name in internal
        if not name.startswith(("ai_engineering_os.domain", "ai_engineering_os.state"))
    )
    assert not illegal, f"{module.name} imports {illegal}"


def test_domain_and_state_import_without_infrastructure() -> None:
    """Verifies importing the pure layers pulls in no web or database machinery."""
    script = (
        "import sys; "
        "import ai_engineering_os.domain, ai_engineering_os.state; "
        "loaded = sorted(m for m in sys.modules "
        "if m.split('.')[0] in {'fastapi','sqlalchemy','asyncpg','starlette','httpx','alembic'}); "
        "print(loaded)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT.parent)},
    )
    assert result.stdout.strip() == "[]"


def test_domain_models_operate_without_a_database(feature: Feature, task: Task) -> None:
    """Verifies domain entities are fully usable with no database connection."""
    assert task.feature_id == feature.id
    assert feature.with_status(feature.status).slug == feature.slug
