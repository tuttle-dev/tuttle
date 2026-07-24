"""Integration tests for application startup.

Verifies that:
- all critical modules can be imported (catches dependency issues),
- the database schema can be materialised in memory,
- the RPC server module loads and dispatches correctly.
"""

import importlib
import sqlite3

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
    "tuttle.app.core.abstractions",
    "tuttle.app.core.database_storage_impl",
    "tuttle.app.core.dispatch",
    "tuttle.app.core.formatting",
    "tuttle.app.core.intent_result",
    "tuttle.app.core.rpc_utils",
    "tuttle.app.auth.intent",
    "tuttle.app.auth.data_source",
    "tuttle.app.clients.intent",
    "tuttle.app.contacts.intent",
    "tuttle.app.contracts.intent",
    "tuttle.app.dashboard.intent",
    "tuttle.app.db.intent",
    "tuttle.app.demo.intent",
    "tuttle.app.invoicing.intent",
    "tuttle.app.llm.intent",
    "tuttle.app.preferences.intent",
    "tuttle.app.projects.intent",
    "tuttle.app.salary.intent",
    "tuttle.app.settings.intent",
    "tuttle.app.tax.intent",
    "tuttle.app.timeline.intent",
    "tuttle.app.timetracking.intent",
    "tuttle.app.users.intent",
    "tuttle.rpc_server",
]


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_import_core_module(module_name):
    """Every core library module must be importable without error."""
    mod = importlib.import_module(module_name)
    assert mod is not None


@pytest.mark.parametrize("module_name", APP_MODULES)
def test_import_app_module(module_name):
    """Every application module must be importable without error."""
    mod = importlib.import_module(module_name)
    assert mod is not None


# ---------------------------------------------------------------------------
# 1b. Resource-module attribute smoke tests
# ---------------------------------------------------------------------------

_RES_ATTRS = [
    (
        "tuttle.app.res.fonts",
        [
            "DEFAULT_FONT",
            "HEADLINE_FONT",
            "APP_FONTS",
            "HEADLINE_0_SIZE",
            "HEADLING_1_SIZE",
            "HEADLINE_2_SIZE",
            "HEADLINE_3_SIZE",
            "HEADLINE_4_SIZE",
            "BODY_1_SIZE",
            "BODY_2_SIZE",
            "SUBTITLE_1_SIZE",
            "SUBTITLE_2_SIZE",
            "BUTTON_SIZE",
            "OVERLINE_SIZE",
            "CAPTION_SIZE",
            "STATUS_BAR_SIZE",
            "BOLD_FONT",
            "BOLDER_FONT",
        ],
    ),
    (
        "tuttle.app.res.colors",
        [
            "bg",
            "bg_surface",
            "bg_surface_hovered",
            "text_primary",
            "text_secondary",
            "text_muted",
            "accent",
            "accent_muted",
            "border",
            "status_active",
            "status_upcoming",
            "status_completed",
        ],
    ),
    (
        "tuttle.app.res.dimens",
        [
            "SPACE_XS",
            "SPACE_SM",
            "SPACE_MD",
            "SPACE_LG",
            "RADIUS_PILL",
            "RADIUS_XL",
        ],
    ),
]


@pytest.mark.parametrize(
    "module_name,attr",
    [(mod, attr) for mod, attrs in _RES_ATTRS for attr in attrs],
    ids=lambda val: val if isinstance(val, str) else "",
)
def test_res_module_attribute_exists(module_name, attr):
    """Every resource constant used by the UI must actually be defined."""
    mod = importlib.import_module(module_name)
    assert hasattr(mod, attr), f"module {module_name!r} has no attribute {attr!r}"


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
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()

    expected_tables = {"user", "contact", "address", "client", "contract", "project"}
    missing = expected_tables - {t.lower() for t in tables}
    assert not missing, f"Missing tables: {missing}"
