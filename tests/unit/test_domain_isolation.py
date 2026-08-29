"""Verifies the domain, state, and rules layers stay pure.

The blueprint requires that ``domain`` depends on nothing but Pydantic and the
standard library, and that ``state`` and ``rules`` depend only on ``domain``. No
domain model may require FastAPI, SQLAlchemy, or PostgreSQL to operate.

``rules`` carries the additional constraint of ADR-004 4.7: it must not depend
on ``state``. Both layers consume the condition vocabulary that ``domain`` owns,
and a rule that imported a lifecycle graph would be answering the state
machine's question rather than its own.
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
RULES_ROOT = SOURCE_ROOT / "rules"

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


# --------------------------------------------------------------------------
# Rules layer isolation (ADR-004 4.4, 4.6, 4.7)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("module", _module_files(RULES_ROOT), ids=lambda p: p.name)
def test_rules_module_has_no_infrastructure_dependency(module: Path) -> None:
    """Verifies no rules module imports a framework, database, or I/O package."""
    forbidden = sorted(_imported_roots(module) & FORBIDDEN_PACKAGES)
    assert not forbidden, f"{module.name} imports {forbidden}"


@pytest.mark.parametrize("module", _module_files(RULES_ROOT), ids=lambda p: p.name)
def test_rules_layer_only_depends_on_the_domain_layer(module: Path) -> None:
    """Verifies rules never reach into state, storage, api, core, events, or client."""
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
        if not name.startswith(("ai_engineering_os.domain", "ai_engineering_os.rules"))
    )
    assert not illegal, f"{module.name} imports {illegal}"


@pytest.mark.parametrize("module", _module_files(RULES_ROOT), ids=lambda p: p.name)
def test_rules_do_not_depend_on_the_state_layer(module: Path) -> None:
    """Verifies the ADR-004 4.7 dependency direction: rules must not import state."""
    source = module.read_text(encoding="utf-8")
    assert "ai_engineering_os.state" not in source, f"{module.name} references the state layer"


@pytest.mark.parametrize("module", _module_files(RULES_ROOT), ids=lambda p: p.name)
def test_the_rule_engine_exposes_no_async_api(module: Path) -> None:
    """Verifies rule evaluation is synchronous, so it needs no event loop or driver."""
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    coroutines = [node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
    assert not coroutines, f"{module.name} declares async functions {coroutines}"
    awaits = [node for node in ast.walk(tree) if isinstance(node, ast.Await)]
    assert not awaits, f"{module.name} awaits a value"


@pytest.mark.parametrize("module", _module_files(RULES_ROOT), ids=lambda p: p.name)
def test_no_rule_accepts_a_repository_or_session_parameter(module: Path) -> None:
    """Verifies facts arrive as a context, never as a data-access handle."""
    tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
    forbidden_parameters = ("session", "repository", "repo", "connection", "engine_url", "db")
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        arguments = [*node.args.args, *node.args.kwonlyargs, *node.args.posonlyargs]
        offenders.extend(
            f"{node.name}({argument.arg})"
            for argument in arguments
            if argument.arg.lower() in forbidden_parameters
        )
    assert not offenders, f"{module.name} declares data-access parameters {offenders}"


def test_importing_rules_loads_no_infrastructure() -> None:
    """Verifies importing the rule layer pulls in no web or database machinery."""
    script = (
        "import sys; "
        "import ai_engineering_os.rules; "
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


def test_importing_rules_does_not_import_the_state_layer() -> None:
    """Verifies the dependency direction holds at runtime, not only in the source."""
    script = (
        "import sys; "
        "import ai_engineering_os.rules; "
        "print(sorted(m for m in sys.modules if m.startswith('ai_engineering_os.state')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT.parent)},
    )
    assert result.stdout.strip() == "[]"


def test_evaluating_every_rule_performs_no_runtime_io() -> None:
    """Verifies purity at runtime, not only by import analysis (ADR-004 4.6).

    A CPython audit hook is installed **after** the facts are built, so it
    observes exactly the evaluation. Import analysis alone would miss I/O reached
    indirectly; this closes that gap.
    """
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "_rule_io_probe.py")],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT.parent)},
    )
    assert result.stdout.strip().endswith("audited_events=[]"), result.stdout


def test_the_condition_vocabulary_is_owned_by_the_domain_layer() -> None:
    """Verifies ADR-004 4.7 relocation, with the state re-export preserved."""
    from ai_engineering_os.domain.conditions import TransitionCondition as DomainCondition
    from ai_engineering_os.state import TransitionCondition as StateCondition
    from ai_engineering_os.state.machine import TransitionCondition as MachineCondition

    assert DomainCondition is StateCondition is MachineCondition
    assert DomainCondition.__module__ == "ai_engineering_os.domain.conditions"
