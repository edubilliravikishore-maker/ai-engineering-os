"""Integration tests for Alembic database migrations."""

from alembic import command
from alembic.config import Config


def test_alembic_migration_upgrade() -> None:
    """Verifies that Alembic can apply migrations up to 'head'."""
    alembic_cfg = Config("alembic.ini")
    # Upgrade to head should execute without error
    command.upgrade(alembic_cfg, "head")


def test_alembic_migration_downgrade_and_reupgrade() -> None:
    """Verifies that Alembic migrations can be rolled back and reapplied."""
    alembic_cfg = Config("alembic.ini")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
