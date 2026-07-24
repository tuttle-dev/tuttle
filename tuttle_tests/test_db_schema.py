"""Tests for tuttle.db_schema — ensure_schema safety guarantees.

These tests verify that the backup/restore mechanism in ensure_schema:

    1. Does NOT destroy databases on transient errors (SQLite lock, I/O
       error, connection refusal) when the schema was not actually modified.
    2. DOES preserve the broken DB and restore the backup when a migration
       partially applied (alembic_version changed but upgrade raised).
    3. Keeps existing data intact through a successful no-op upgrade.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator
from unittest.mock import patch

import pytest
from alembic import command
from sqlalchemy import create_engine, text

import tuttle.model  # noqa: F401
from tuttle.db_schema import (
    SchemaMigrationError,
    _alembic_config_for,
    _get_current_revision,
    ensure_schema,
)


@pytest.fixture
def seeded_db(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    """Create a DB at head with a sentinel row in the user table."""
    db = tmp_path / "test-user.db"
    url = f"sqlite:///{db}"
    cfg = _alembic_config_for(url)
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user (id, name, subtitle, email, operating_country) "
                "VALUES (1, 'Test User', 'Tester', 'test@example.com', 'Germany')"
            )
        )
    engine.dispose()
    yield db, url


def test_transient_error_does_not_destroy_database(
    seeded_db: tuple[Path, str],
) -> None:
    """A transient error (e.g. SQLite lock) must NOT move the DB to .broken-*."""
    db, url = seeded_db

    with patch.object(command, "upgrade", side_effect=OSError("database is locked")):
        with pytest.raises(SchemaMigrationError, match="transient"):
            ensure_schema(url)

    assert db.exists(), "Database file should still exist after transient error"
    assert not list(db.parent.glob("*.broken-*")), "No .broken-* file should be created for transient errors"

    engine = create_engine(url)
    with engine.begin() as conn:
        row = conn.execute(text("SELECT name FROM user WHERE id = 1")).fetchone()
    engine.dispose()
    assert row is not None and row[0] == "Test User", "Data must be preserved"


def test_transient_error_preserves_backup(seeded_db: tuple[Path, str]) -> None:
    """The pre-upgrade backup should still exist after a transient failure."""
    db, url = seeded_db

    with patch.object(command, "upgrade", side_effect=RuntimeError("disk I/O error")):
        with pytest.raises(SchemaMigrationError):
            ensure_schema(url)

    backups = list(db.parent.glob("*.bak-*"))
    assert len(backups) >= 1, "Backup should be preserved"


def test_partial_migration_marks_db_broken(tmp_path: Path) -> None:
    """If alembic_version changes but upgrade raises, DB is marked broken."""
    db = tmp_path / "partial.db"
    url = f"sqlite:///{db}"
    cfg = _alembic_config_for(url)
    command.upgrade(cfg, "head")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO user (id, name, subtitle, email, operating_country) "
                "VALUES (1, 'Victim', '', 'v@x.com', 'Germany')"
            )
        )
    engine.dispose()

    original_revision = _get_current_revision(url)

    def _simulate_partial_migration(cfg, target):
        """Simulate a migration that changes alembic_version then crashes."""
        engine = create_engine(url)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM alembic_version"))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('CORRUPTED')"))
        engine.dispose()
        raise RuntimeError("Migration crashed mid-way")

    with patch.object(command, "upgrade", side_effect=_simulate_partial_migration):
        with pytest.raises(SchemaMigrationError, match="Migration crashed"):
            ensure_schema(url)

    broken_files = list(tmp_path.glob("*.broken-*"))
    assert len(broken_files) == 1, "Broken DB should be preserved"

    assert db.exists(), "Main DB path should be restored from backup"
    restored_rev = _get_current_revision(url)
    assert restored_rev == original_revision, "Restored DB should be at the original revision"


def test_noop_upgrade_preserves_data(seeded_db: tuple[Path, str]) -> None:
    """Running ensure_schema on an already-at-head DB must not lose data."""
    db, url = seeded_db

    ensure_schema(url)

    engine = create_engine(url)
    with engine.begin() as conn:
        row = conn.execute(text("SELECT name FROM user WHERE id = 1")).fetchone()
    engine.dispose()
    assert row is not None and row[0] == "Test User"


def test_multiple_transient_errors_never_destroy_db(
    seeded_db: tuple[Path, str],
) -> None:
    """Even repeated transient failures must not accumulate .broken-* files."""
    db, url = seeded_db

    for _ in range(5):
        with patch.object(command, "upgrade", side_effect=OSError("database is locked")):
            with pytest.raises(SchemaMigrationError):
                ensure_schema(url)

    broken_files = list(db.parent.glob("*.broken-*"))
    assert len(broken_files) == 0, f"Repeated transient errors created {len(broken_files)} broken files"

    engine = create_engine(url)
    with engine.begin() as conn:
        row = conn.execute(text("SELECT name FROM user WHERE id = 1")).fetchone()
    engine.dispose()
    assert row is not None and row[0] == "Test User"
