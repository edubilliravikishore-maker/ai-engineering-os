"""Unit tests for AI Engineering OS configuration settings."""

from ai_engineering_os.config import Settings


def test_default_settings() -> None:
    """Verifies that default settings load as expected."""
    settings = Settings()
    assert settings.app_name == "AI Engineering OS"
    assert settings.app_env in ["development", "test", "production"]
    assert settings.app_port == 8000
    assert settings.postgres_port == 5432
    assert settings.postgres_db == "ai_engineering_os"
    assert "postgresql+asyncpg://" in settings.async_database_url
    assert settings.max_inline_evidence_bytes == 5 * 1024 * 1024


def test_custom_database_url_override() -> None:
    """Verifies that setting a custom DATABASE_URL adapts to asyncpg."""
    custom_url = "postgresql://myuser:mypass@dbhost:5433/mydb"
    settings = Settings(database_url=custom_url)
    assert settings.async_database_url == "postgresql+asyncpg://myuser:mypass@dbhost:5433/mydb"


def test_explicit_asyncpg_database_url() -> None:
    """Verifies that an explicit asyncpg URL is preserved."""
    custom_url = "postgresql+asyncpg://myuser:mypass@dbhost:5433/mydb"
    settings = Settings(database_url=custom_url)
    assert settings.async_database_url == custom_url
