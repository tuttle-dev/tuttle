"""make contact first_name and last_name non-nullable

Revision ID: c3d70beffa72
Revises: f8a4403a2ecd
Create Date: 2026-07-08 10:14:13.875899

======================================================================
FROZEN HISTORICAL SNAPSHOT — NOT THE SCHEMA SOURCE OF TRUTH.

The source of truth is tuttle/model.py. This file captures the schema
DELTA from the previous revision to this point in history. It is
APPEND-ONLY: once committed, never edit it. To change the schema, edit
tuttle/model.py and run `just migrate "<msg>"` to ADD a new revision.

Reading this file to learn the current schema is a MISTAKE — it is a
point-in-time snapshot. Read tuttle/model.py instead.
======================================================================

MANDATORY REVIEW CHECKLIST before committing this file:

1. RENAMES — autogenerate emits drop_column + add_column for renames,
   which DESTROYS DATA. If you intended a rename, replace the pair with
   op.alter_column(<table>, <old>, new_column_name=<new>).

2. NO MODEL IMPORTS — never `from tuttle.model import ...` here.
   Model classes drift over time; this script must be pinned to the
   schema at this point in history. For data transformations, declare
   a local sa.table(...) snapshot with only the columns this revision
   touches.

3. BATCH MODE — render_as_batch=True rebuilds tables for SQLite. After
   a batch op on a table with foreign keys, verify integrity inside the
   migration: op.execute("PRAGMA foreign_key_check").

See tuttle/migrations/README.md.
----------------------------------------------------------------------
"""

# pyright: reportAttributeAccessIssue=false
# sqlmodel.sql.sqltypes is a submodule resolved at runtime; basedpyright
# does not statically expose `sql` as an attribute of `sqlmodel`.
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes  # noqa: F401 — ensures runtime resolution of AutoString
from alembic import op

revision: str = "c3d70beffa72"
down_revision: Union[str, Sequence[str], None] = "f8a4403a2ecd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Backfill any existing NULLs before adding NOT NULL constraint
    contact = sa.table(
        "contact",
        sa.column("first_name", sa.VARCHAR()),
        sa.column("last_name", sa.VARCHAR()),
    )
    # Backfill NULLs with "Unknown" rather than "" so existing contacts remain
    # editable; the new validator rejects empty strings.
    op.execute(contact.update().where(contact.c.first_name.is_(None)).values(first_name="Unknown"))
    op.execute(contact.update().where(contact.c.last_name.is_(None)).values(last_name="Unknown"))

    with op.batch_alter_table("contact", schema=None) as batch_op:
        batch_op.alter_column("first_name", existing_type=sa.VARCHAR(), nullable=False)
        batch_op.alter_column("last_name", existing_type=sa.VARCHAR(), nullable=False)

    op.execute("PRAGMA foreign_key_check")


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/c3d70beffa72_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
