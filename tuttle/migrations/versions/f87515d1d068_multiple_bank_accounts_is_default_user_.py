"""multiple bank accounts: is_default/user_id on bankaccount, contract.bank_account_id

Revision ID: f87515d1d068
Revises: 9cad5ae77a79
Create Date: 2026-08-10 18:10:41.686326

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

revision: str = "f87515d1d068"
down_revision: Union[str, Sequence[str], None] = "9cad5ae77a79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("bankaccount", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_bankaccount_user_id_user", "user", ["user_id"], ["id"], ondelete="CASCADE")

    # Backfill while user.bank_account_id still exists: the account the user
    # had in the old 1:1 becomes the owner (BankAccount.user_id) and the
    # default. Accounts that were never linked stay owned by nobody, and only
    # the linked one is marked default.
    bankaccount = sa.table(
        "bankaccount",
        sa.column("id", sa.Integer),
        sa.column("user_id", sa.Integer),
        sa.column("is_default", sa.Boolean),
    )
    user = sa.table(
        "user",
        sa.column("id", sa.Integer),
        sa.column("bank_account_id", sa.Integer),
    )
    op.execute(
        bankaccount.update().values(
            user_id=sa.select(user.c.id).where(user.c.bank_account_id == bankaccount.c.id).scalar_subquery(),
        )
    )
    op.execute(
        bankaccount.update()
        .values(is_default=True)
        .where(bankaccount.c.id.in_(sa.select(user.c.bank_account_id).where(user.c.bank_account_id.is_not(None))))
    )

    with op.batch_alter_table("contract", schema=None) as batch_op:
        batch_op.add_column(sa.Column("bank_account_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_contract_bank_account_id_bankaccount", "bankaccount", ["bank_account_id"], ["id"], ondelete="SET NULL"
        )

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("bank_account_id")

    op.execute("PRAGMA foreign_key_check")


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/f87515d1d068_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
