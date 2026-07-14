"""Centralized application database.

Manages ``app.db`` in the Tuttle data directory (see :func:`tuttle.data_dir.get_data_dir`).
Stores:
- **registered_user** — the user registry (one row per Tuttle user)
- **app_setting** — key-value store for app-wide settings (LLM config, theme, …)

Per-user business data lives in separate ``<slug>.db`` files in the same directory.
"""

import datetime
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .data_dir import get_data_dir

from loguru import logger
from sqlalchemy import event
from sqlmodel import Field, Session, SQLModel, create_engine, select


# ---------------------------------------------------------------------------
# Models (use a dedicated MetaData so they never collide with per-user tables)
# ---------------------------------------------------------------------------

_app_metadata = SQLModel.metadata


class RegisteredUser(SQLModel, table=True):
    __tablename__ = "registered_user"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    subtitle: str = ""
    db_file: str = Field(sa_column_kwargs={"unique": True})
    is_demo: bool = False
    created_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
    )
    last_active_at: Optional[datetime.datetime] = None


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_setting"

    key: str = Field(primary_key=True)
    value: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    """Turn a display name into a safe filename slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "user"


def _unique_db_file(app_dir: Path, base_slug: str) -> str:
    """Return a db filename that doesn't clash with existing files."""
    candidate = f"{base_slug}.db"
    if not (app_dir / candidate).exists():
        return candidate
    n = 2
    while (app_dir / f"{base_slug}-{n}.db").exists():
        n += 1
    return f"{base_slug}-{n}.db"


# ---------------------------------------------------------------------------
# AppDatabase
# ---------------------------------------------------------------------------


class AppDatabase:
    """Facade for the centralized ``app.db``."""

    def __init__(self, app_dir: Optional[Path] = None):
        self.app_dir = app_dir or get_data_dir()
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.app_dir / "app.db"
        self._engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        event.listen(
            self._engine,
            "connect",
            lambda dbapi_conn, _: dbapi_conn.execute("PRAGMA foreign_keys = ON"),
        )
        self.ensure()

    def ensure(self):
        """Create the app tables if they don't exist.

        Called from __init__ so any reader (e.g. tuttle.fx asking for the
        primary currency) works before the app has run its startup path.
        Scoped to the two app tables: SQLModel's metadata is shared with
        tuttle.model, and an unscoped create_all would mirror every
        per-user business table into app.db.
        """
        _app_metadata.create_all(
            self._engine, tables=[RegisteredUser.__table__, AppSetting.__table__]
        )

    def _session(self) -> Session:
        return Session(self._engine, expire_on_commit=False)

    # -- User registry ------------------------------------------------------

    def list_users(self) -> List[RegisteredUser]:
        with self._session() as s:
            return list(
                s.exec(select(RegisteredUser).order_by(RegisteredUser.name)).all()
            )

    def get_user_by_db_file(self, db_file: str) -> Optional[RegisteredUser]:
        with self._session() as s:
            return s.exec(
                select(RegisteredUser).where(RegisteredUser.db_file == db_file)
            ).first()

    def add_user(
        self,
        name: str,
        subtitle: str = "",
        is_demo: bool = False,
        db_file: Optional[str] = None,
    ) -> RegisteredUser:
        if db_file is None:
            db_file = _unique_db_file(self.app_dir, _slugify(name))
        user = RegisteredUser(
            name=name,
            subtitle=subtitle,
            db_file=db_file,
            is_demo=is_demo,
        )
        with self._session() as s:
            s.add(user)
            s.commit()
            s.refresh(user)
        return user

    def remove_user(self, db_file: str) -> bool:
        with self._session() as s:
            user = s.exec(
                select(RegisteredUser).where(RegisteredUser.db_file == db_file)
            ).first()
            if not user:
                return False
            s.delete(user)
            s.commit()
        db_path = self.app_dir / db_file
        if db_path.exists():
            db_path.unlink()
            logger.info(f"Deleted user database: {db_path}")
        return True

    def set_active(self, db_file: str):
        with self._session() as s:
            user = s.exec(
                select(RegisteredUser).where(RegisteredUser.db_file == db_file)
            ).first()
            if user:
                user.last_active_at = datetime.datetime.now()
                s.add(user)
                s.commit()

    def get_last_active(self) -> Optional[RegisteredUser]:
        with self._session() as s:
            return s.exec(
                select(RegisteredUser)
                .where(RegisteredUser.last_active_at.isnot(None))  # type: ignore[union-attr]
                .order_by(RegisteredUser.last_active_at.desc())  # type: ignore[union-attr]
            ).first()

    def get_user_db_path(self, db_file: str) -> Path:
        return self.app_dir / db_file

    # -- Settings -----------------------------------------------------------

    def get_setting(self, key: str) -> Optional[str]:
        with self._session() as s:
            row = s.get(AppSetting, key)
            return row.value if row else None

    def set_setting(self, key: str, value: Any):
        str_value = value if isinstance(value, str) else json.dumps(value)
        with self._session() as s:
            row = s.get(AppSetting, key)
            if row:
                row.value = str_value
            else:
                row = AppSetting(key=key, value=str_value)
            s.add(row)
            s.commit()

    def get_all_settings(self, prefix: Optional[str] = None) -> Dict[str, str]:
        with self._session() as s:
            stmt = select(AppSetting)
            if prefix:
                stmt = stmt.where(AppSetting.key.startswith(prefix))  # type: ignore[union-attr]
            rows = s.exec(stmt).all()
            return {r.key: r.value for r in rows}

    def delete_setting(self, key: str):
        with self._session() as s:
            row = s.get(AppSetting, key)
            if row:
                s.delete(row)
                s.commit()

    # -- LLM config convenience (replaces llm_config.json) ------------------

    _LLM_KEYS = (
        "llm.provider",
        "llm.base_url",
        "llm.model",
        "llm.api_key",
        "llm.request_timeout",
    )

    def get_llm_config(self) -> Dict[str, Any]:
        settings = self.get_all_settings(prefix="llm.")
        return {
            "provider": settings.get("llm.provider", "ollama"),
            "base_url": settings.get("llm.base_url", "http://localhost:11434"),
            "model": settings.get("llm.model", ""),
            "api_key": settings.get("llm.api_key", ""),
            "request_timeout": float(settings.get("llm.request_timeout", "600")),
        }

    def save_llm_config(self, config: dict):
        for short_key in (
            "provider",
            "base_url",
            "model",
            "api_key",
            "request_timeout",
        ):
            if short_key in config:
                self.set_setting(f"llm.{short_key}", str(config[short_key]))

    # -- Migration from legacy llm_config.json ------------------------------

    def migrate_llm_config_from_json(self):
        """One-time import of llm_config.json into app.db settings."""
        json_path = self.app_dir / "llm_config.json"
        if not json_path.exists():
            return
        existing = self.get_all_settings(prefix="llm.")
        if existing:
            return
        try:
            data = json.loads(json_path.read_text())
            self.save_llm_config(data)
            logger.info("Migrated LLM config from llm_config.json to app.db")
        except Exception as e:
            logger.warning(f"Failed to migrate LLM config: {e}")
