"""Alembic environment for Tuttle.

target_metadata is bound to SQLModel.metadata so that
`alembic revision --autogenerate` diffs the live database against the
classes in tuttle/model.py. The model file is the single source of truth;
this file only configures how Alembic reads it.

render_as_batch=True is required because user databases are SQLite and
SQLite cannot ALTER columns in place — Alembic must rebuild the table.

See tuttle/migrations/README.md for the full workflow.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import tuttle.model  # noqa: F401 — registers every SQLModel table on SQLModel.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Programmatic callers (tuttle.db_schema.ensure_schema) override sqlalchemy.url
# via cfg.set_main_option. For CLI usage (alembic revision --autogenerate ...)
# an env var override lets developers target a temp/dev SQLite without editing
# alembic.ini.
_env_url = os.environ.get("TUTTLE_DB_URL")
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url)

target_metadata = SQLModel.metadata

# tuttle/app_db.py declares RegisteredUser / AppSetting on the same global
# SQLModel.metadata. Those tables belong to the central app.db, NOT the
# per-user databases this Alembic chain manages. Exclude them so the user-DB
# migrations stay scoped to user data.
_APP_REGISTRY_TABLES = {"registered_user", "app_setting"}


def _include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name in _APP_REGISTRY_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        include_object=_include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live SQLite database (the normal path)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            include_object=_include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
