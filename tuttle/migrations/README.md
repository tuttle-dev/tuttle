# Tuttle Database Migrations

Alembic-managed schema migrations for per-user SQLite databases.

## The principle

`tuttle/model.py` is the **single source of truth** for the database
schema. Alembic's `--autogenerate` diffs `SQLModel.metadata` against the
live database and emits only the delta. Migration scripts in
`versions/` contain `op.create_table(...)`, `op.add_column(...)`,
`op.alter_column(...)` — never redeclarations of the full model.

## Why `versions/0001_initial_schema.py` looks like a model redefinition

Because the v1.0 baseline migration is "from empty → full schema", it
unavoidably contains `op.create_table(...)` for every model. This is
how every migration system works (Alembic, Django, Rails, Flyway). It
is a **frozen historical snapshot**, not a second source of truth:

- Existing files in `versions/` are **immutable**. Once committed,
  never edit them. Future schema changes ADD new revision files.
- After three or four future revisions, `0001` will be visibly out of
  date vs `model.py`. That divergence is the structural signal that
  `versions/` is history, not truth.
- The full schema at any commit = `SQLModel.metadata` (truth) = the
  chain `0001 → 0002 → ... → head` applied in order. Both are
  equivalent representations; only `model.py` is editable.

Do not read `versions/*.py` to learn the current schema. Read
`model.py`.

## Workflow

After ANY change to a SQLModel class in `tuttle/model.py`:

```bash
just migrate "describe the change"
# alias for:
# TUTTLE_DB_URL="sqlite:///<a reference DB>" alembic revision --autogenerate -m "..."
```

Open the generated `versions/NNNN_*.py` and review:

1. **Renames** — autogenerate emits `op.drop_column(...)` +
   `op.add_column(...)` for renames, which **destroys data**. If you
   intended a rename, replace the pair with
   `op.alter_column("<table>", "<old>", new_column_name="<new>")`.

2. **Data transformations** — never `from tuttle.model import ...`
   inside a migration. Models drift; each script must be pinned to the
   schema at its point in history. Use a local `sa.table()` snapshot
   with only the columns this revision touches:

   ```python
   def upgrade() -> None:
       invoice = sa.table(
           "invoice",
           sa.column("id", sa.Integer),
           sa.column("document_type", sa.String),
       )
       op.execute(invoice.update().values(document_type="invoice").where(invoice.c.document_type.is_(None)))
   ```

3. **Batch-mode FK integrity** — `render_as_batch=True` is required for
   SQLite, but it rebuilds tables (create new → copy → drop → rename).
   After any batch op on a table involved in foreign-key relationships
   (`invoice`, `client`, `project`, `contract`, `timesheet`,
   `timetrackingitem`), append a check inside the revision:

   ```python
   op.execute("PRAGMA foreign_key_check")
   ```

Commit `model.py` **and** the new migration script in the same commit.

## Downgrades are not supported

Every revision's `downgrade()` raises `NotImplementedError`. Tuttle is a
single-user desktop app — rolling back a schema is destructive (data in
dropped columns is gone forever) and offers nothing over restoring the
`.bak-<ts>` snapshot that `ensure_schema()` takes before every upgrade.

To "undo" a migration during development: delete the revision file,
`just reset`, regenerate.

## Verifying chain integrity

`tuttle_tests/test_migrations.py` runs on every PR. It:

- Builds a DB at the previous head, inserts rows, upgrades to current
  head, and asserts no rows were lost. This catches accidental
  drop+add pairs from misread renames.
- Asserts the final schema matches `SQLModel.metadata`.
- Runs `PRAGMA foreign_key_check` after upgrade.
- Statically (AST) asserts no `versions/*.py` script imports from
  `tuttle.model`.

If a test fails, your migration is incorrect — do not silence it.

## Runtime invocation

`tuttle/db_schema.py::ensure_schema(db_url)` is the only entry point.
It is called when:

- A user is switched (`tuttle/app/users/intent.py::_switch_to_user_db`)
- A user is registered (same module, `create`)
- The DB storage layer initialises (`app/core/database_storage_impl.py`)

`ensure_schema` does, in order:

1. Copy `<db>` to `<db>.bak-<ts>` (last 5 backups kept).
2. `alembic upgrade head` against `<db>`.
3. On failure: rename the half-migrated DB to `<db>.broken-<ts>`,
   restore the backup in its place, raise `SchemaMigrationError`.

The UI layer (RPC dispatcher) is expected to surface
`SchemaMigrationError` to the user instead of silently continuing with
a corrupt DB.

## Dev drift footgun

`SQLModel.create_all` (used previously) silently created missing tables
and columns. Alembic does **not**. If you edit `model.py` but forget to
run `just migrate`, the next launch will look fine — until you try to
insert a row that touches the new column and SQLite raises
`no such column`.

`just check-migrations` runs `alembic check`, which fails if
`model.py` and `versions/` diverge. Wire it into CI.

## Why this layout

| Component | Why |
|---|---|
| `env.py` binds `target_metadata = SQLModel.metadata` | One source of truth |
| `render_as_batch=True` in `env.py` | SQLite cannot `ALTER` columns in place |
| `script.py.mako` carries a review checklist | Every new revision is born self-documenting |
| `db_schema.py` is a thin caller | Avoids mixing schema definition and orchestration |
| Backup → upgrade → restore-on-fail in `ensure_schema` | First user must never lose data |

See also: `.cursor/rules/schema-migrations.mdc` (agent-facing rule),
`tuttle/model.py` (source of truth), `tuttle/db_schema.py` (orchestration).
