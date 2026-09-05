# Database Schema Changes

`tuttle/model.py` is the SINGLE SOURCE OF TRUTH for the database schema.
Alembic in `tuttle/migrations/` derives all DDL from `SQLModel.metadata`.

Applies to: `tuttle/model.py`, `tuttle/db_schema.py`, `tuttle/migrations/**/*.py`, `tuttle/app_db.py`

## Critical: versions/*.py are frozen snapshots, NOT source of truth

Files in `tuttle/migrations/versions/` are APPEND-ONLY historical
records. They look like schema definitions because they contain
`op.create_table(...)` calls, but they capture the schema at a point
in time — not the current schema.

DO NOT:
- Read `versions/*.py` to learn the current schema. Read `model.py`.
- Edit any existing file in `versions/`. Once committed, a revision is
  immutable.
- Hand-write a new revision file. Always go through `just migrate`.

DO:
- Edit `tuttle/model.py` for schema changes, then `just migrate "<msg>"`
  to ADD a new revision.
- Treat each `versions/NNNN_*.py` as a sealed migration step. The chain
  of all revisions applied in order reproduces the current schema.

## When editing tuttle/model.py

After ANY change to a SQLModel class (new column, renamed field, new
table, new relationship) you MUST:

  1. `just migrate "<describe change>"`   (alias for `alembic revision --autogenerate`)
  2. Open the generated `tuttle/migrations/versions/*.py`
  3. CHECK FOR `drop_column` + `add_column` PAIRS — autogenerate misreads
     renames as drop+add, which destroys data. Use `op.alter_column(...,
     new_column_name=...)` for renames.
  4. Commit `model.py` AND the new migration script TOGETHER.

## Inside tuttle/migrations/versions/*.py

NEVER `from tuttle.model import ...`. Models drift; migration scripts
must be pinned to the schema at their point in history.

For data transformations use a local `sa.table()` snapshot with only the
columns this revision touches:

```python
invoice = sa.table("invoice",
                   sa.column("id", sa.Integer),
                   sa.column("document_type", sa.String))
op.execute(invoice.update().values(document_type="invoice"))
```

After a batch op on a table with foreign keys (`invoice`, `client`,
`project`, `contract`, `timesheet`, `timetrackingitem`), verify
integrity inside the revision:

```python
op.execute("PRAGMA foreign_key_check")
```

## tuttle/db_schema.py

Thin Alembic caller (backup → `command.upgrade` → restore on failure).
NEVER add `ALTER TABLE` strings or column dicts here. If you find
yourself wanting to, you are working against the design.

## Downgrades are not supported

The `downgrade()` function in every revision must raise
`NotImplementedError`. Tuttle is a single-user desktop app: rolling back
a schema is destructive (data in dropped columns is gone) and offers
nothing over restoring a `.bak-<ts>` snapshot taken by
`ensure_schema()` before the upgrade.

If you're iterating on a migration during development and want to
"undo": delete the revision file in `versions/`, run `just reset` to
wipe `~/.tuttle`, and regenerate.

## tuttle_tests/test_migrations.py

Don't bypass these tests. They catch silent data-loss bugs that the
autogenerator cannot detect on its own.

See `tuttle/migrations/README.md` for the full rationale.
