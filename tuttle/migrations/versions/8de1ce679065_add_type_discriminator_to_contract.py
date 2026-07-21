"""add type discriminator to contract

Revision ID: 8de1ce679065
Revises: 34dd17917a18
Create Date: 2026-06-28 14:38:25.581818

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

revision: str = "8de1ce679065"
down_revision: Union[str, Sequence[str], None] = "34dd17917a18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Adds the ``type`` discriminator (defaults all rows to ``time_based``),
    then backfills it from existing data and removes any ambiguity:

    - A contract with a positive ``fixed_price`` becomes ``fixed_price``.
      (If a legacy row had BOTH a rate and a fixed price — the bug this
      revision closes — fixed_price wins, as the stronger commitment.)
    - The value column that does not match the chosen type is nulled, so
      no row carries both ``rate`` and ``fixed_price`` afterwards.
    """
    with op.batch_alter_table("contract", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "type",
                sa.Enum("time_based", "fixed_price", name="contracttype"),
                server_default="time_based",
                nullable=False,
            )
        )

    contract = sa.table(
        "contract",
        sa.column("id", sa.Integer),
        sa.column("type", sa.String),
        sa.column("rate", sa.Numeric),
        sa.column("fixed_price", sa.Numeric),
    )
    op.execute(
        contract.update()
        .where(contract.c.fixed_price.isnot(None))
        .where(contract.c.fixed_price > 0)
        .values(type="fixed_price")
    )
    op.execute(contract.update().where(contract.c.type == "fixed_price").values(rate=None))
    op.execute(contract.update().where(contract.c.type == "time_based").values(fixed_price=None))
    op.execute("PRAGMA foreign_key_check")


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/8de1ce679065_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
