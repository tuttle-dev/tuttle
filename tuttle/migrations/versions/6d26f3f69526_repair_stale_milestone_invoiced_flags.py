"""repair stale milestone invoiced flags

Revision ID: 6d26f3f69526
Revises: 5688486cf305
Create Date: 2026-09-20 21:20:24.302938

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

revision: str = "6d26f3f69526"
down_revision: Union[str, Sequence[str], None] = "5688486cf305"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Reopen milestones whose invoices were all cancelled or deleted.

    Cancelling or deleting a deposit or final invoice used to leave its
    milestones flagged as invoiced, so they could never be billed again. A
    milestone stays invoiced only while a live deposit references it or a
    live final invoice settles its contract.
    """
    milestone = sa.table(
        "paymentmilestone",
        sa.column("id", sa.Integer),
        sa.column("contract_id", sa.Integer),
        sa.column("invoiced", sa.Boolean),
    )
    invoice = sa.table(
        "invoice",
        sa.column("contract_id", sa.Integer),
        sa.column("milestone_id", sa.Integer),
        sa.column("document_type", sa.String),
        sa.column("cancelled", sa.Boolean),
    )

    live = sa.or_(invoice.c.cancelled.is_(None), invoice.c.cancelled == sa.false())
    covered_by_deposit = sa.exists().where(invoice.c.milestone_id == milestone.c.id, live)
    settled_by_final = sa.exists().where(
        invoice.c.contract_id == milestone.c.contract_id,
        invoice.c.document_type == "final",
        live,
    )

    op.execute(
        milestone.update()
        .where(milestone.c.invoiced == sa.true(), ~covered_by_deposit, ~settled_by_final)
        .values(invoiced=False)
    )


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/6d26f3f69526_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
