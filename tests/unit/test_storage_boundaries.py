"""Architectural boundaries of the persistence layer (ADR-005 5.11, 5.13).

These tests exist because the boundaries they pin are invisible at runtime. A
leaked ORM object still works; a `storage` import inside `rules` still works. The
damage shows up much later, as a rule that quietly loads its own facts.

They run **without a database**, alongside the rest of the Checkpoint 3 suite.
"""

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

import ai_engineering_os.rules as rules_package
import ai_engineering_os.storage as storage_package
from ai_engineering_os.domain.base import DomainModel
from ai_engineering_os.storage.database import Base

SOURCE_ROOT = Path(storage_package.__file__).resolve().parent.parent


def _modules_of(package: object) -> list[str]:
    """Returns every importable module name inside ``package``."""
    path = Path(package.__file__).resolve().parent  # type: ignore[attr-defined]
    name = package.__name__  # type: ignore[attr-defined]
    found = [name]
    for module in pkgutil.walk_packages([str(path)], prefix=f"{name}."):
        found.append(module.name)
    return found


def _imports_of(module_name: str) -> set[str]:
    """Returns every module imported by ``module_name``, read from its source."""
    module = importlib.import_module(module_name)
    source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[arg-type]
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module)
    return imported


STORAGE_MODULES = _modules_of(storage_package)
RULES_MODULES = _modules_of(rules_package)


def test_the_storage_layer_has_modules_to_check() -> None:
    """Guards against the boundary tests passing vacuously."""
    assert len(STORAGE_MODULES) >= 25
    assert len(RULES_MODULES) >= 8


@pytest.mark.parametrize("module_name", STORAGE_MODULES)
def test_storage_never_imports_rules(module_name: str) -> None:
    """Persistence must not depend on the Rule Engine.

    ADR-005 builds the repositories the Checkpoint 6 context loader will read
    from; it does **not** build the loader. An import in this direction would be
    that loader appearing a checkpoint early.
    """
    offending = {
        name for name in _imports_of(module_name) if name.startswith("ai_engineering_os.rules")
    }
    assert not offending, f"{module_name} imports {sorted(offending)}"


@pytest.mark.parametrize("module_name", RULES_MODULES)
def test_rules_never_imports_storage_or_sqlalchemy(module_name: str) -> None:
    """The Rule Engine must stay persistence-agnostic (ADR-004 4.4).

    A rule that can fetch its own facts can fetch different facts on two
    identical calls, which destroys reproducibility.
    """
    imported = _imports_of(module_name)
    forbidden = {
        name
        for name in imported
        if name.startswith(("ai_engineering_os.storage", "sqlalchemy", "alembic", "asyncpg"))
    }
    assert not forbidden, f"{module_name} imports {sorted(forbidden)}"


@pytest.mark.parametrize("module_name", RULES_MODULES)
def test_rules_never_imports_state(module_name: str) -> None:
    """`rules` must not depend on `state` (ADR-004 4.7); both consume `domain`."""
    offending = {n for n in _imports_of(module_name) if n.startswith("ai_engineering_os.state")}
    assert not offending, f"{module_name} imports {sorted(offending)}"


def test_no_orm_model_is_exported_from_the_storage_package() -> None:
    """A SQLAlchemy model never crosses the repository boundary (ADR-005 5.11)."""
    exported = {name: getattr(storage_package, name) for name in storage_package.__all__}
    leaked = {
        name
        for name, value in exported.items()
        if isinstance(value, type) and issubclass(value, Base) and value is not Base
    }
    assert not leaked, f"storage exports ORM models: {sorted(leaked)}"


def test_every_repository_read_returns_a_domain_type() -> None:
    """Repository return annotations name domain types, never ORM rows (ADR-005 5.11)."""
    from ai_engineering_os.storage import repositories as repository_package

    for module_name in _modules_of(repository_package):
        module = importlib.import_module(module_name)
        source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[arg-type]
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.AsyncFunctionDef) or node.name.startswith("_"):
                continue
            annotation = ast.unparse(node.returns) if node.returns else "None"
            assert "Row" not in annotation, (
                f"{module_name}.{node.name} returns {annotation}, which names an ORM row"
            )


def test_no_repository_orders_or_filters_by_persistence_metadata() -> None:
    """Metadata timestamps are never used for ordering or selection (ADR-005 5.9).

    They are exactly the shape of the "latest QA report" mechanism ADR-004 4.15
    forbids inventing, so the prohibition is pinned rather than remembered.
    """
    from ai_engineering_os.storage import mappers as mapper_package
    from ai_engineering_os.storage import repositories as repository_package

    metadata_columns = {"row_created_at", "row_updated_at"}

    for package in (repository_package, mapper_package):
        for module_name in _modules_of(package):
            module = importlib.import_module(module_name)
            source = Path(module.__file__).read_text(encoding="utf-8")  # type: ignore[arg-type]
            # AST rather than text: a docstring may name these columns to explain
            # the prohibition; only executable code may not reference them.
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Attribute):
                    assert node.attr not in metadata_columns, f"{module_name}: .{node.attr}"
                elif isinstance(node, ast.Name):
                    assert node.id not in metadata_columns, f"{module_name}: {node.id}"
                elif (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and node.value in metadata_columns
                ):
                    raise AssertionError(f"{module_name}: {node.value!r} used as a value")


def test_append_only_tables_carry_no_version_column() -> None:
    """A row that is never updated cannot lose an update race (ADR-005 5.6)."""
    append_only = {
        "task_revisions",
        "evidence_records",
        "qa_reports",
        "qa_defects",
        "review_decisions",
        "decisions",
        "decision_acknowledgements",
        "os_events",
        "state_transitions_audit",
    }
    mutable = {"actors", "features", "feature_plans", "tasks", "work_packages"}

    for name in append_only:
        assert "version" not in Base.metadata.tables[name].columns, name
    for name in mutable:
        assert "version" in Base.metadata.tables[name].columns, name


def test_the_event_and_audit_tables_landed_at_checkpoint_five() -> None:
    """`os_events` and `state_transitions_audit` are delivered here (ADR-005 5.13, ADR-006).

    This assertion is the inverse of the one Checkpoint 4 carried. The tables
    were absent by ruling then and are present by ruling now; the count is
    pinned in both directions so neither an omission nor an unrecorded
    fifteenth table passes unnoticed.
    """
    assert "os_events" in Base.metadata.tables
    assert "state_transitions_audit" in Base.metadata.tables
    assert len(Base.metadata.tables) == 16


def test_the_ordering_key_is_database_generated_and_not_application_supplied() -> None:
    """`sequence_number` is GENERATED ALWAYS, so code cannot override it (ADR-006 6.1)."""
    for name in ("os_events", "state_transitions_audit"):
        column = Base.metadata.tables[name].columns["sequence_number"]
        assert column.identity is not None, name
        assert column.identity.always is True, name
        assert not column.nullable, name


def test_only_the_os_may_be_recorded_without_an_actor() -> None:
    """The absent Actor id is bound to OS and to nothing else (ADR-006 6.8)."""
    pairs = {
        "os_events": ("actor_role", "actor_id"),
        "state_transitions_audit": ("requested_by_role", "requested_by"),
    }
    for name, (role_column, id_column) in pairs.items():
        table = Base.metadata.tables[name]
        assert table.columns[id_column].nullable, name
        assert not table.columns[role_column].nullable, name
        guard = next(
            c for c in table.constraints if c.name and c.name.endswith("actorless_only_for_os")
        )
        text = str(guard.sqltext)  # type: ignore[attr-defined]
        assert role_column in text and id_column in text and "OS" in text, name


def test_no_repository_for_an_append_only_table_can_update_or_delete() -> None:
    """Append-only is enforced by the absence of a code path (ADR-005 5.4, 5.7, 5.8)."""
    from ai_engineering_os.storage.repositories.event_repo import EventRepository
    from ai_engineering_os.storage.repositories.transition_audit_repo import (
        TransitionAuditRepository,
    )

    for repository in (EventRepository, TransitionAuditRepository):
        public = {name for name in dir(repository) if not name.startswith("_")}
        assert not public & {"save", "update", "delete", "remove"}, repository.__name__


def test_no_deferred_lifecycle_state_is_admitted_by_any_constraint() -> None:
    """D-1 BLOCKED and D-6 stop/abandon states are not persistable (ADR-005 5.7)."""
    forbidden = ("ABANDONED", "CANCELLED", "STOPPED")
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            text = str(getattr(constraint, "sqltext", ""))
            for state in forbidden:
                assert state not in text, f"{table.name}: {state} admitted by {constraint.name}"

    # QAStatus.BLOCKED is a QA report outcome, not the deferred D-1 lifecycle state.
    task_status = next(
        c for c in Base.metadata.tables["tasks"].constraints if c.name == "ck_tasks_status"
    )
    assert "BLOCKED" not in str(task_status.sqltext)  # type: ignore[attr-defined]


def test_qa_defect_scope_columns_remain_nullable() -> None:
    """Unresolved scope must stay representable (ADR-004 4.8)."""
    defects = Base.metadata.tables["qa_defects"]
    assert defects.columns["scope_task_id"].nullable
    assert defects.columns["scope_feature_id"].nullable
    assert defects.columns["scope_task_id"].foreign_keys
    assert defects.columns["scope_feature_id"].foreign_keys


def test_task_plan_linkage_is_mandatory() -> None:
    """ADR-003 3.12 and ADR-004 4.8 make both columns required."""
    tasks = Base.metadata.tables["tasks"]
    assert not tasks.columns["feature_plan_id"].nullable
    assert not tasks.columns["plan_definition_key"].nullable


def test_task_revisions_carry_no_status_column() -> None:
    """ADR-003 3.1: a Revision has no active/superseded marker."""
    assert "status" not in Base.metadata.tables["task_revisions"].columns


def test_no_qa_report_recency_or_latest_marker_exists() -> None:
    """The authoritative QA-result mechanism is not invented here (ADR-004 4.15)."""
    columns = set(Base.metadata.tables["qa_reports"].columns.keys())
    for invented in (
        "sequence_number",
        "is_latest",
        "is_current",
        "current_report_id",
        "supersedes",
    ):
        assert invented not in columns


def test_tasks_carry_no_reviewer_column() -> None:
    """REVIEWER_ASSIGNED remains a BLOCKED_CONDITION; no routing model exists."""
    columns = set(Base.metadata.tables["tasks"].columns.keys())
    assert not {c for c in columns if "reviewer" in c}


def test_every_foreign_key_restricts_deletion() -> None:
    """RESTRICT everywhere; no automatic cascading deletion (ADR-005 5.7, 5.15)."""
    for table in Base.metadata.tables.values():
        for key in table.foreign_keys:
            assert key.ondelete == "RESTRICT", f"{table.name}.{key.parent.name}"
            assert key.onupdate is None, f"{table.name}.{key.parent.name} sets ON UPDATE"


def test_domain_models_remain_frozen() -> None:
    """Persistence did not loosen the domain layer to make mapping easier."""
    assert DomainModel.model_config["frozen"] is True
