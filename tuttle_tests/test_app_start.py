"""Integration tests for application startup.

Verifies that:
- all critical modules can be imported (catches dependency issues),
- the database schema can be materialised in memory,
- the app process starts without an immediate crash.
"""

import importlib
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from sqlmodel import SQLModel, create_engine


# ---------------------------------------------------------------------------
# 1. Import smoke tests
# ---------------------------------------------------------------------------

CORE_MODULES = [
    "tuttle",
    "tuttle.model",
    "tuttle.calendar",
    "tuttle.invoicing",
    "tuttle.timetracking",
    "tuttle.rendering",
    "tuttle.tax",
    "tuttle.banking",
    "tuttle.time",
    "tuttle.dataviz",
    "tuttle.os_functions",
    "tuttle.mail",
]

APP_MODULES = [
    "tuttle.app",
    "tuttle.app.core.abstractions",
    "tuttle.app.core.database_storage_impl",
    "tuttle.app.core.views",
    "tuttle.app.auth.view",
    "tuttle.app.home.view",
    "tuttle.app.projects.view",
    "tuttle.app.contracts.view",
    "tuttle.app.invoicing.view",
    "tuttle.app.timetracking.view",
    "tuttle.app.preferences.view",
]


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_import_core_module(module_name):
    """Every core library module must be importable without error."""
    mod = importlib.import_module(module_name)
    assert mod is not None


@pytest.mark.parametrize("module_name", APP_MODULES)
def test_import_app_module(module_name):
    """Every application UI module must be importable without error."""
    mod = importlib.import_module(module_name)
    assert mod is not None


# ---------------------------------------------------------------------------
# 2. Database schema creation
# ---------------------------------------------------------------------------


def test_database_schema_creation(tmp_path):
    """The full SQLModel schema must materialise as SQLite tables."""
    import tuttle.model  # noqa: F401 — registers all tables

    db_path = tmp_path / "test_startup.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()

    expected_tables = {"user", "contact", "address", "client", "contract", "project"}
    missing = expected_tables - {t.lower() for t in tables}
    assert not missing, f"Missing tables: {missing}"


# ---------------------------------------------------------------------------
# 3. Application process smoke test
# ---------------------------------------------------------------------------

APP_ENTRY_POINT = Path(__file__).resolve().parent.parent / "app.py"
STARTUP_WAIT_SECONDS = 5


@pytest.mark.gui
def test_app_process_starts():
    """The application process must survive initial startup without crashing."""
    # start_new_session gives the app its own process group so we can
    # kill it together with any child processes (e.g. the Flet desktop client).
    proc = subprocess.Popen(
        [sys.executable, str(APP_ENTRY_POINT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        time.sleep(STARTUP_WAIT_SECONDS)
        exit_code = proc.poll()
        if exit_code is not None:
            _, stderr = proc.communicate(timeout=2)
            pytest.fail(
                f"App exited prematurely with code {exit_code}.\n"
                f"stderr:\n{stderr.decode(errors='replace')}"
            )
    finally:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGKILL)
        proc.wait(timeout=5)
