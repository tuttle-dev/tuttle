"""require contract on project

Revision ID: 386a8e1294ef
Revises: 6d26f3f69526
Create Date: 2026-09-21 11:40:05.769705

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
from alembic import context, op

revision: str = "386a8e1294ef"
down_revision: Union[str, Sequence[str], None] = "6d26f3f69526"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    A project without a contract cannot be invoiced, forecast or reported on,
    and guessing a contract for it would corrupt the user's books, so such
    projects are removed and the user is told which ones to recreate.
    """
    conn = op.get_bind()

    orphans = conn.execute(sa.text("SELECT title FROM project WHERE contract_id IS NULL ORDER BY title")).fetchall()
    if orphans:
        titles = ", ".join(f"'{row[0]}'" for row in orphans)
        if len(orphans) == 1:
            notice = (
                f"During the update, the project {titles} was removed because it had no contract. "
                "Every project must belong to a contract: create the contract, then add the project again. "
                "Its details are still in the pre-update backup in the Tuttle data folder."
            )
        else:
            notice = (
                f"During the update, {len(orphans)} projects were removed because they had no contract: {titles}. "
                "Every project must belong to a contract: create their contracts, then add the projects again. "
                "Their details are still in the pre-update backup in the Tuttle data folder."
            )
        context.config.attributes.setdefault("notices", []).append(notice)

        # Invoices and timesheets are financial records: detach them rather than delete them.
        conn.execute(
            sa.text(
                "UPDATE invoice SET project_id = NULL WHERE project_id IN (SELECT id FROM project WHERE contract_id IS NULL)"
            )
        )
        conn.execute(
            sa.text(
                "UPDATE timesheet SET project_id = NULL WHERE project_id IN (SELECT id FROM project WHERE contract_id IS NULL)"
            )
        )
        conn.execute(sa.text("DELETE FROM project WHERE contract_id IS NULL"))

    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.alter_column("contract_id", existing_type=sa.INTEGER(), nullable=False)

    op.execute("PRAGMA foreign_key_check")


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/386a8e1294ef_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError("Downgrades are not supported. Restore from a .bak-<ts> snapshot instead.")
