"""Per-user-database schema lifecycle.

This module does NOT define schema. It runs Alembic against each user's
SQLite file at app start, upgrading it to the head revision derived from
tuttle/model.py.

To change the schema: edit tuttle/model.py, then run
`just migrate "<describe change>"` (alias for `alembic revision
--autogenerate`). Do NOT add ALTER TABLE statements here.

See tuttle/migrations/README.md.

Failure model:
- Before upgrade, the SQLite file is copied to <db>.bak-<ts>. The last
  MAX_BACKUPS are kept per database; older ones are pruned.
- If `command.upgrade` raises, the partially migrated DB is renamed to
  <db>.broken-<ts>, the most recent backup is restored in its place,
  and a SchemaMigrationError is raised so the UI/RPC layer can surface
  it. The app must not continue with a corrupt DB.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from loguru import logger

import tuttle.model  # noqa: F401 — ensure all table classes are registered

MAX_BACKUPS = 5


class SchemaMigrationError(RuntimeError):
    """Raised when Alembic migration of a user database fails.

    Carries the path of the broken DB (renamed to .broken-<ts>) and the
    backup that was restored in its place so the UI can surface both.
    """

    def __init__(
        self,
        message: str,
        *,
        broken_db: Path | None = None,
        restored_from: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.broken_db = broken_db
        self.restored_from = restored_from


def _project_root() -> Path:
    """Locate the directory containing alembic.ini.

    When frozen by PyInstaller, alembic.ini and the migrations/ tree are
    bundled under sys._MEIPASS. In dev (or tests) they live at the repo
    root. We resolve relative to this module: tuttle/db_schema.py sits
    one level below the alembic.ini location.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _alembic_config_for(db_url: str) -> Config:
    """Build an Alembic Config bound to the given database URL.

    script_location and sqlalchemy.url are set programmatically so the
    same config object works for any user DB and for both dev and frozen
    deployments.
    """
    root = _project_root()
    ini = root / "alembic.ini"
    cfg = Config(str(ini)) if ini.exists() else Config()
    cfg.set_main_option("script_location", str(root / "tuttle" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _db_path_from_url(db_url: str) -> Path | None:
    """Extract the local filesystem path from a sqlite:/// URL, if any."""
    prefix = "sqlite:///"
    if not db_url.startswith(prefix):
        return None
    return Path(db_url[len(prefix) :])


def _backup(db_path: Path) -> Path | None:
    """Create a timestamped copy of the DB next to the original.

    Returns the backup path, or None if the DB does not exist yet (fresh
    install / first run for this user — nothing to back up).
    """
    if not db_path.exists():
        return None
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_suffix(db_path.suffix + f".bak-{ts}")
    shutil.copy2(db_path, backup_path)
    logger.debug(f"Schema backup: {backup_path.name}")
    _prune_backups(db_path)
    return backup_path


def _prune_backups(db_path: Path) -> None:
    """Keep at most MAX_BACKUPS for this DB, oldest pruned first."""
    pattern = db_path.name + ".bak-*"
    backups = sorted(db_path.parent.glob(pattern), key=lambda p: p.stat().st_mtime)
    for old in backups[:-MAX_BACKUPS]:
        try:
            old.unlink()
            logger.debug(f"Pruned old backup: {old.name}")
        except OSError as e:
            logger.warning(f"Could not prune backup {old}: {e}")


def _get_current_revision(db_url: str) -> str | None:
    """Read the current alembic_version from the database, or None."""
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception:
        return None
    finally:
        engine.dispose()


def ensure_schema(db_url: str) -> None:
    """Upgrade the database at db_url to the current head revision.

    For SQLite URLs, takes a timestamped backup before upgrading. If
    upgrade fails AND the migration partially applied (alembic_version
    changed), the DB is presumed corrupt: it is preserved as
    .broken-<ts> and the backup is restored.

    Transient errors (SQLite locked, I/O errors, no-op upgrade failures)
    that leave the schema unchanged do NOT mark the DB as broken — the
    error is simply re-raised so the caller can retry.
    """
    cfg = _alembic_config_for(db_url)
    db_path = _db_path_from_url(db_url)
    backup_path = _backup(db_path) if db_path is not None else None

    revision_before = _get_current_revision(db_url) if db_path else None

    try:
        command.upgrade(cfg, "head")
        logger.debug(f"Schema ensured for {db_url}")
    except Exception as exc:
        logger.exception(f"Schema migration failed for {db_url}")

        revision_after = _get_current_revision(db_url) if db_path else None
        schema_was_modified = revision_before != revision_after

        if not schema_was_modified:
            logger.warning("Migration error was transient (schema unchanged) — database NOT marked as broken.")
            raise SchemaMigrationError(
                f"Schema migration failed (transient): {exc}",
                broken_db=None,
                restored_from=None,
            ) from exc

        broken_path = None
        if db_path is not None and db_path.exists():
            ts = time.strftime("%Y%m%d-%H%M%S")
            broken_path = db_path.with_suffix(db_path.suffix + f".broken-{ts}")
            try:
                db_path.rename(broken_path)
                logger.error(f"Broken DB preserved at: {broken_path}")
            except OSError as rename_err:
                logger.error(f"Could not preserve broken DB: {rename_err}")
                broken_path = None
        if backup_path is not None and backup_path.exists():
            try:
                shutil.copy2(backup_path, db_path)  # type: ignore[arg-type]
                logger.info(f"Restored pre-migration backup: {backup_path.name}")
            except OSError as restore_err:
                logger.error(f"Could not restore backup: {restore_err}")
        raise SchemaMigrationError(
            f"Schema migration failed: {exc}",
            broken_db=broken_path,
            restored_from=backup_path,
        ) from exc
