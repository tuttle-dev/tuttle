"""revert contact name fields to optional with empty default

Revision ID: bac018e35ce6
Revises: 4447db01f757
Create Date: 2026-07-26 11:55:54.559439

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

revision: str = "bac018e35ce6"
down_revision: Union[str, Sequence[str], None] = "4447db01f757"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    contact = sa.table(
        "contact",
        sa.column("first_name", sa.VARCHAR()),
        sa.column("last_name", sa.VARCHAR()),
    )
    # Reconcile both database populations from #429:
    # - pre-9cec3e0 databases have "" (original backfill)  → keep as-is
    # - post-9cec3e0 databases have "Unknown" (bad backfill) → revert to ""
    op.execute(contact.update().where(contact.c.first_name == "Unknown").values(first_name=""))
    op.execute(contact.update().where(contact.c.last_name == "Unknown").values(last_name=""))

    with op.batch_alter_table("contact", schema=None) as batch_op:
        batch_op.alter_column(
            "first_name",
            existing_type=sa.VARCHAR(),
            nullable=True,
            server_default="",
        )
        batch_op.alter_column(
            "last_name",
            existing_type=sa.VARCHAR(),
            nullable=True,
            server_default="",
        )

    op.execute("PRAGMA foreign_key_check")


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/bac018e35ce6_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
