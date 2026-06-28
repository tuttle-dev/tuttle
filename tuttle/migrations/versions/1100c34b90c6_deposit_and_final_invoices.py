"""deposit and final invoices

Revision ID: 1100c34b90c6
Revises: 34dd17917a18
Create Date: 2026-06-28 10:36:58.702409

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

revision: str = "1100c34b90c6"
down_revision: Union[str, Sequence[str], None] = "9cad5ae77a79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Idempotent: a prior failed run may have created ``paymentmilestone`` before
    the invoice batch step failed (SQLite DDL is not transactional).  Re-running
    must not error on objects that already exist.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "paymentmilestone" not in tables:
        op.create_table(
            "paymentmilestone",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("contract_id", sa.Integer(), nullable=False),
            sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("percentage", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("invoiced", sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(["contract_id"], ["contract.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    invoice_cols = {c["name"] for c in inspector.get_columns("invoice")}
    with op.batch_alter_table("invoice", schema=None) as batch_op:
        if "deposit_for_id" not in invoice_cols:
            batch_op.add_column(sa.Column("deposit_for_id", sa.Integer(), nullable=True))
        if "milestone_id" not in invoice_cols:
            batch_op.add_column(sa.Column("milestone_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_invoice_deposit_for_id", "invoice", ["deposit_for_id"], ["id"])
        batch_op.create_foreign_key(
            "fk_invoice_milestone_id",
            "paymentmilestone",
            ["milestone_id"],
            ["id"],
        )

    op.execute("PRAGMA foreign_key_check")


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/1100c34b90c6_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
