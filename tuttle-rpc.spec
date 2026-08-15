# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the tuttle RPC core.

Bundles tuttle/rpc_server.py as the entry point, pulling in the full
CPython interpreter, the entire tuttle package, all Python dependencies,
native shared libraries, and data files.  The output is a self-contained
directory (dist/tuttle-rpc/) that runs without a Python installation.

Usage:
    pyinstaller tuttle-rpc.spec
"""

import sys
from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# ---------------------------------------------------------------------------
# Data files that PyInstaller can't discover from imports alone
# ---------------------------------------------------------------------------

datas = [
    ("templates", "templates"),
    ("tuttle/tax_data", "tuttle/tax_data"),
    # Alembic migration scripts are loaded by path at runtime, so
    # PyInstaller's import analyzer cannot discover them. Bundle the
    # whole migrations tree (env.py, script.py.mako, versions/*.py)
    # plus the alembic.ini so ensure_schema() can locate them via
    # sys._MEIPASS when frozen. Without this, the packaged .app fails
    # to migrate per-user DBs on first launch.
    ("tuttle/migrations", "tuttle/migrations"),
    ("alembic.ini", "."),
]

# rfc3987_syntax ships non-Python data files that PyInstaller misses
_rfc_spec = find_spec("rfc3987_syntax")
if _rfc_spec and _rfc_spec.submodule_search_locations:
    datas.append((_rfc_spec.submodule_search_locations[0], "rfc3987_syntax"))

# drafthorse ships Factur-X / ZUGFeRD XSD schemas as package data;
# PyInstaller can't discover them from imports alone.
_drafthorse_spec = find_spec("drafthorse")
if _drafthorse_spec and _drafthorse_spec.submodule_search_locations:
    _dh_schema = Path(_drafthorse_spec.submodule_search_locations[0]) / "schema"
    if _dh_schema.is_dir():
        datas.append((str(_dh_schema), "drafthorse/schema"))

# ---------------------------------------------------------------------------
# Hidden imports -- lazily imported modules PyInstaller can't trace
# ---------------------------------------------------------------------------

# Intent classes are loaded dynamically by the dispatcher (importlib) on the
# first RPC call, so PyInstaller's static analyzer can't trace them. Auto-collect
# every submodule of tuttle.app instead of hand-listing them — a hand-maintained
# list silently drops any newly added domain from the frozen build (e.g. the
# 'imports' domain regression).
hiddenimports = collect_submodules("tuttle.app") + [
    # Supporting modules
    "tuttle.app.core.database_storage_impl",
    "tuttle.app.core.formatting",
    "tuttle.model",
    "tuttle.demo",
    "tuttle.db_schema",
    # LLM providers
    "llama_index.llms.ollama",
    "llama_index.llms.openai_like",
    "llama_index.llms.openai",
    "openai",
    # Babel number/currency formatting
    "babel.numbers",
    # SQLModel / SQLAlchemy backends
    "sqlmodel",
    "sqlalchemy.dialects.sqlite",
    # Alembic — env.py is imported by path at runtime, so nothing it imports
    # is visible to the analyzer. logging.config only ever reached the bundle
    # as a transitive import of the notebook dev dependencies; when those were
    # dropped, every migration in the frozen build started failing.
    "logging.config",
    "logging.handlers",
    "alembic",
    "alembic.config",
    "alembic.command",
    "alembic.script",
    "alembic.runtime.migration",
    "alembic.autogenerate",
    "mako",
    "mako.template",
    # PDF rendering (C++ engine with prebuilt binaries, no system dependencies)
    "plutoprint",
    # Other potentially dynamic imports
    "pycountry",
    "pycountry.databases",
    "faker",
    "faker.providers",
    "ics",
    "loguru",
    "pandera",
    "PyPDF2",
    "fitz",  # pymupdf
]

# ---------------------------------------------------------------------------
# Excludes -- large packages the RPC server never imports
# ---------------------------------------------------------------------------

excludes = [
    "tkinter",
    "_tkinter",
]

# ---------------------------------------------------------------------------
# Analysis & build
# ---------------------------------------------------------------------------

a = Analysis(
    ["tuttle/rpc_server.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="tuttle-rpc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # RPC server communicates via stdio
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="tuttle-rpc",
)
