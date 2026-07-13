"""Migration chain integrity tests.

Every PR that changes tuttle/model.py must come with a matching Alembic
revision. These tests prove the upgrade chain is:

    1. Complete — DB at the previous head can be upgraded to current head.
    2. Non-destructive — rows inserted before the upgrade survive it.
    3. Faithful — the resulting schema matches SQLModel.metadata.
    4. FK-clean — PRAGMA foreign_key_check is empty after upgrade.

If autogenerate ever emits a drop_column + add_column pair instead of a
rename (the silent-data-loss footgun), the row-survival assertion catches
it before the migration reaches a user.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterator

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlmodel import SQLModel

import tuttle.model  # noqa: F401 — ensure tables register on SQLModel.metadata
from tuttle.db_schema import _alembic_config_for


def _seed_value(col_type: object) -> object:
    """Return a SQLite-compatible sentinel for a NOT NULL column of any type.

    The chain test only cares about row IDENTITY surviving across the
    upgrade; the specific values are irrelevant. Match by SQL type name
    so we satisfy the schema's NOT NULL / type constraints.
    """
    t = str(col_type).upper()
    if "INT" in t or "NUMERIC" in t or "DECIMAL" in t or "FLOAT" in t or "REAL" in t:
        return 0
    if "BOOL" in t:
        return 0
    if "DATE" in t and "TIME" in t:
        return "2026-01-01 00:00:00"
    if "DATE" in t:
        return "2026-01-01"
    if "TIME" in t:
        return "00:00:00"
    return ""


def _heads(db_url: str) -> tuple[str | None, str]:
    """Return (previous_revision, current_head) for the migrations chain."""
    cfg = _alembic_config_for(db_url)
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    assert head, "No Alembic head revision found"
    revisions = list(script.walk_revisions())
    previous = revisions[1].revision if len(revisions) > 1 else None
    return previous, head


@pytest.fixture
def tmp_db(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    db = tmp_path / "user.db"
    yield db, f"sqlite:///{db}"


def test_single_head_no_branch_conflicts() -> None:
    """Migration chain must have exactly one head — no unresolved branches.

    Multiple heads mean two migrations share the same down_revision,
    which breaks `alembic upgrade head` (it doesn't know which path to
    take).  Fix by rebasing one migration onto the other.
    """
    from alembic.script import ScriptDirectory

    cfg = _alembic_config_for("sqlite:///")
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, (
        f"Migration chain has {len(heads)} heads: {heads}. "
        f"Expected exactly 1. Rebase one migration to depend on the other."
    )


def test_upgrade_from_empty_creates_full_schema(tmp_db: tuple[Path, str]) -> None:
    """Per-user-DB schema matches SQLModel.metadata after upgrade to head.

    The app.db registry tables (registered_user, app_setting) share the
    same global metadata but are explicitly excluded from per-user-DB
    migrations via include_object in env.py — see migrations/env.py.
    """
    db, url = tmp_db
    cfg = _alembic_config_for(url)
    command.upgrade(cfg, "head")

    excluded = {"registered_user", "app_setting"}
    engine = create_engine(url)
    try:
        live_tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        expected = set(SQLModel.metadata.tables.keys()) - excluded
        assert live_tables == expected, (
            f"Schema diverged from model. "
            f"Missing: {expected - live_tables}, extra: {live_tables - expected}"
        )
    finally:
        engine.dispose()


def test_upgrade_chain_is_non_destructive(tmp_db: tuple[Path, str]) -> None:
    """Rows inserted at the previous head must survive the upgrade to head.

    Skipped when only one revision exists (initial baseline) — the test
    becomes meaningful as soon as a second revision is added.
    """
    db, url = tmp_db
    previous, head = _heads(url)
    if previous is None:
        pytest.skip("Only the baseline revision exists; nothing to chain-test yet.")

    cfg = _alembic_config_for(url)
    command.upgrade(cfg, previous)

    excluded = {"registered_user", "app_setting"}
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            live = set(inspect(conn).get_table_names())
            for table_name in SQLModel.metadata.tables:
                if table_name in excluded or table_name not in live:
                    continue
                cols_info = inspect(conn).get_columns(table_name)
                col_names = {c["name"] for c in cols_info}
                if "id" not in col_names:
                    continue
                values: dict[str, object] = {"id": 9999}
                for col in cols_info:
                    if col["name"] == "id" or col.get("nullable", True):
                        continue
                    values[col["name"]] = _seed_value(col["type"])
                placeholders = ", ".join(f":{k}" for k in values)
                cols_str = ", ".join(values)
                conn.execute(
                    text(
                        f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
                    ),
                    values,
                )
        with engine.begin() as conn:
            live = set(inspect(conn).get_table_names())
            row_counts_before = {
                t: conn.exec_driver_sql(f"SELECT COUNT(*) FROM {t}").scalar()
                for t in SQLModel.metadata.tables
                if t in live and t not in excluded
            }
    finally:
        engine.dispose()

    command.upgrade(cfg, head)

    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            for t, expected_count in row_counts_before.items():
                actual = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {t}").scalar()
                assert actual == expected_count, (
                    f"Table {t}: {expected_count} rows before upgrade, {actual} after. "
                    f"Migration is destructive — check for unintended drop_column/add_column pairs."
                )
    finally:
        engine.dispose()


def test_foreign_key_check_clean_after_upgrade(tmp_db: tuple[Path, str]) -> None:
    db, url = tmp_db
    cfg = _alembic_config_for(url)
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db)
    try:
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert violations == [], (
            f"Foreign key violations after upgrade: {violations}. "
            f"Likely a batch-mode op forgot to re-attach an FK."
        )
    finally:
        conn.close()


def test_versions_are_append_only_in_git() -> None:
    """Existing revisions in versions/ must not be edited after commit.

    Each revision captures the schema delta at one point in history.
    Editing an already-committed revision corrupts the chain for any
    database that already advanced past it. Schema changes must always
    ADD a new revision via `just migrate`.

    This test enforces the rule by checking git history: every file in
    versions/ must have a single commit (the one that introduced it),
    or any subsequent commits must only modify docstrings/comments —
    never op.* calls.

    Skipped outside a git checkout (e.g. wheel installs).
    """
    import subprocess

    versions = (
        Path(__file__).resolve().parent.parent / "tuttle" / "migrations" / "versions"
    )
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=versions,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("Not a git checkout; cannot enforce append-only.")

    offenders: list[str] = []
    for script in versions.glob("*.py"):
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H", "--", script.name],
            cwd=versions,
            capture_output=True,
            text=True,
        )
        commits = [c for c in result.stdout.strip().splitlines() if c]
        if len(commits) <= 1:
            continue
        # Diff only post-creation commits (exclude oldest = creation commit)
        oldest = commits[-1]
        diff = subprocess.run(
            ["git", "diff", f"{oldest}..HEAD", "--", script.name],
            cwd=versions,
            capture_output=True,
            text=True,
        )
        for line in diff.stdout.splitlines():
            if line.startswith("+    op."):
                offenders.append(script.name)
                break

    assert not offenders, (
        f"These migration scripts have post-commit edits to op.* calls: {offenders}. "
        f"Revisions are append-only — schema changes must ADD a new revision via "
        f"`just migrate`, not edit existing ones."
    )


def test_downgrades_are_not_supported() -> None:
    """Every revision's downgrade() must raise NotImplementedError.

    Tuttle is single-user desktop; data restoration goes through the
    .bak-<ts> snapshots, never through schema downgrade. The template
    enforces this; this test guards against a hand-edited revision that
    re-introduces a real downgrade body.
    """
    import ast

    versions = (
        Path(__file__).resolve().parent.parent / "tuttle" / "migrations" / "versions"
    )
    offenders: list[str] = []
    for script in versions.glob("*.py"):
        tree = ast.parse(script.read_text(), filename=str(script))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
                raises_notimpl = any(
                    isinstance(stmt, ast.Raise)
                    and isinstance(stmt.exc, ast.Call)
                    and getattr(stmt.exc.func, "id", "") == "NotImplementedError"
                    for stmt in node.body
                )
                if not raises_notimpl:
                    offenders.append(script.name)
                break
    assert not offenders, (
        f"These revisions have a real downgrade() body: {offenders}. "
        f"Replace with `raise NotImplementedError(...)` — see script.py.mako."
    )


def test_no_model_imports_in_versions() -> None:
    """Migration scripts must not import from tuttle.model.

    Models drift over time; each script must be pinned to its point in
    history via local sa.table() snapshots. AST-based so docstring text
    that mentions the forbidden pattern doesn't trip the check.
    """
    import ast

    versions = (
        Path(__file__).resolve().parent.parent / "tuttle" / "migrations" / "versions"
    )
    offenders: list[str] = []
    for script in versions.glob("*.py"):
        tree = ast.parse(script.read_text(), filename=str(script))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "tuttle.model"
            ):
                offenders.append(script.name)
                break
            if isinstance(node, ast.Import) and any(
                n.name.startswith("tuttle.model") for n in node.names
            ):
                offenders.append(script.name)
                break
    assert not offenders, (
        f"These migration scripts import tuttle.model, which breaks when the "
        f"model evolves: {offenders}. Use a local sa.table(...) snapshot instead."
    )


# -- Tax category backfill (revision 5f919b074635) ----------------------------

_TAX_CATEGORY_REVISION = "5f919b074635"
_BEFORE_TAX_CATEGORY = "16093a6ceba4"


def _insert(cur: sqlite3.Cursor, table: str, **values: object) -> None:
    """Insert a row, filling any other NOT NULL column with a placeholder."""
    info = list(cur.execute(f"PRAGMA table_info({table})"))
    row = dict(values)
    for _cid, name, typ, notnull, default, pk in info:
        if name in row or pk or not notnull or default is not None:
            continue
        row[name] = _seed_value(typ)
    cols = ", ".join(f'"{k}"' for k in row)
    marks = ", ".join("?" for _ in row)
    cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(row.values()))


def _seed_contract(cur, cid, client_id, vat_rate, title):
    _insert(
        cur,
        "contract",
        id=cid,
        title=title,
        client_id=client_id,
        VAT_rate=vat_rate,
        currency="EUR",
        start_date="2024-01-01",
        unit="hour",
        type="time_based",
        rate=100,
    )
    _insert(
        cur,
        "project",
        id=cid,
        title=f"p{cid}",
        tag=f"#t{cid}",
        contract_id=cid,
        start_date="2024-01-01",
    )
    _insert(
        cur,
        "invoice",
        id=cid,
        number=f"INV{cid}",
        date="2024-02-01",
        contract_id=cid,
        project_id=cid,
        document_type="invoice",
    )
    _insert(
        cur,
        "invoiceitem",
        id=cid,
        quantity=1,
        unit="hour",
        unit_price=100,
        description="work",
        VAT_rate=vat_rate,
        invoice_id=cid,
    )


@pytest.fixture
def backfilled_db(tmp_db: tuple[Path, str]):
    """A DB seeded at the revision before the tax category, then upgraded."""
    db, url = tmp_db
    cfg = _alembic_config_for(url)
    command.upgrade(cfg, _BEFORE_TAX_CATEGORY)

    con = sqlite3.connect(db)
    cur = con.cursor()
    for aid, country in [(1, "United States"), (2, "France"), (3, "Germany"), (4, "")]:
        _insert(cur, "address", id=aid, country=country)
    for cid, aid, name in [
        (1, 1, "US Corp"),
        (2, 2, "FR SARL"),
        (3, 3, "DE GmbH"),
        (4, 4, "Nowhere Ltd"),
    ]:
        _insert(cur, "client", id=cid, name=name, address_id=aid)

    _seed_contract(cur, 1, 1, 0.0, "us-zero")
    _seed_contract(cur, 2, 2, 0.0, "fr-zero")
    _seed_contract(cur, 3, 3, 0.19, "de-standard")
    _seed_contract(cur, 4, 4, 0.0, "unknown-country-zero")
    _seed_contract(cur, 5, 1, 0.19, "us-standard")
    # A 0% line under a taxed contract: zero-rated, never outside scope.
    _insert(
        cur,
        "invoiceitem",
        id=99,
        quantity=1,
        unit="hour",
        unit_price=50,
        description="freebie",
        VAT_rate=0.0,
        invoice_id=5,
    )
    con.commit()
    con.close()

    command.upgrade(cfg, _TAX_CATEGORY_REVISION)
    con = sqlite3.connect(db)
    yield con
    con.close()


@pytest.mark.parametrize(
    "title,expected",
    [
        ("us-zero", "outside_scope"),  # 0% to a non-EU client
        ("fr-zero", "zero_rated"),  # 0% inside the EU VAT area
        ("de-standard", "standard"),
        ("us-standard", "standard"),
        # An unresolvable country keeps the historical reading rather than
        # silently reclassifying the invoice as outside the scope of tax.
        ("unknown-country-zero", "zero_rated"),
    ],
)
def test_contract_tax_category_backfill(backfilled_db, title, expected):
    row = backfilled_db.execute(
        'SELECT "VAT_category" FROM contract WHERE title = ?', (title,)
    ).fetchone()
    assert row[0] == expected


def test_invoice_item_inherits_contract_category(backfilled_db):
    row = backfilled_db.execute(
        'SELECT i."VAT_category" FROM invoiceitem i '
        "JOIN invoice v ON v.id = i.invoice_id "
        "JOIN contract c ON c.id = v.contract_id WHERE c.title = 'us-zero'"
    ).fetchone()
    assert row[0] == "outside_scope"


def test_zero_rate_line_under_taxed_contract_is_zero_rated(backfilled_db):
    """Must not become O — that would mix categories and violate BR-O-11/12."""
    row = backfilled_db.execute(
        'SELECT "VAT_category" FROM invoiceitem WHERE description = ?', ("freebie",)
    ).fetchone()
    assert row[0] == "zero_rated"


def test_backfill_leaves_no_null_categories(backfilled_db):
    for table in ("contract", "invoiceitem"):
        count = backfilled_db.execute(
            f'SELECT COUNT(*) FROM {table} WHERE "VAT_category" IS NULL'
        ).fetchone()[0]
        assert count == 0, f"{table} has NULL VAT_category rows"
