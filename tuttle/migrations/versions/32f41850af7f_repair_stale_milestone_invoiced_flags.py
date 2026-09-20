"""repair stale milestone invoiced flags

Revision ID: 32f41850af7f
Revises: 5688486cf305
Create Date: 2026-09-20 21:11:19.384530

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

revision: str = "32f41850af7f"
down_revision: Union[str, Sequence[str], None] = "5688486cf305"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Repair milestones that are marked invoiced but have no live deposit invoice."""
    milestone = sa.table(
        "paymentmilestone",
        sa.column("id", sa.Integer),
        sa.column("invoiced", sa.Boolean),
    )
    invoice = sa.table(
        "invoice",
        sa.column("id", sa.Integer),
        sa.column("milestone_id", sa.Integer),
        sa.column("cancelled", sa.Boolean),
    )

    # A milestone is stale-invoiced when invoiced=True but no non-cancelled
    # deposit invoice references it.
    stale_ids = (
        sa.select(milestone.c.id)
        .where(milestone.c.invoiced == True)  # noqa: E712
        .where(
            ~sa.exists(
                sa.select(sa.literal(1))
                .where(invoice.c.milestone_id == milestone.c.id)
                .where(sa.or_(invoice.c.cancelled == False, invoice.c.cancelled.is_(None)))  # noqa: E712
            )
        )
    )

    op.execute(milestone.update().where(milestone.c.id.in_(stale_ids)).values(invoiced=False))


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/32f41850af7f_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
