"""add tax category to contract and invoice item, tax number to user

Revision ID: 5f919b074635
Revises: 8ec5efc5316d
Create Date: 2026-07-10 12:05:31.686760

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

from alembic import op
import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes  # noqa: F401 — ensures runtime resolution of AutoString

revision: str = "5f919b074635"
down_revision: Union[str, Sequence[str], None] = "8ec5efc5316d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Pinned snapshot of the EU VAT area at this revision.
# fmt: off
_EU_VAT_COUNTRIES = frozenset(
    {
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
        "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
        "NL", "PL", "PT", "RO", "SE", "SI", "SK",
    }
)
# fmt: on


def _resolve_iso(name: str) -> Union[str, None]:
    """Country name → ISO 3166-1 alpha-2, or None if unresolvable.

    ``lookup`` already matches the alpha-2, alpha-3, name, official name and
    common name. No fuzzy fallback: a guess here silently reclassifies the tax
    category of an issued invoice, and an unresolvable country has a defined
    behaviour already (see ``_zero_rate_category``).
    """
    if not name or not name.strip():
        return None
    import pycountry

    try:
        return pycountry.countries.lookup(name.strip()).alpha_2
    except LookupError:
        return None


def _zero_rate_category(country: str, cache: dict) -> str:
    """Which category a 0% supply belongs to, given the client's country.

    A 0% supply to a recipient outside the EU VAT area is not zero-rated but
    outside the scope of tax (EN16931 category O). When the country cannot be
    resolved we keep the historical 'zero_rated' reading rather than silently
    reclassifying an invoice.
    """
    if country not in cache:
        iso = _resolve_iso(country)
        cache[country] = (
            "zero_rated" if iso is None or iso in _EU_VAT_COUNTRIES else "outside_scope"
        )
    return cache[country]


def _backfill(conn) -> None:
    contracts = conn.execute(
        sa.text(
            'SELECT c.id AS id, c."VAT_rate" AS vat_rate, '
            "COALESCE(a.country, '') AS country "
            "FROM contract c "
            "LEFT JOIN client cl ON cl.id = c.client_id "
            "LEFT JOIN address a ON a.id = cl.address_id"
        )
    ).fetchall()

    cache: dict = {}
    for row in contracts:
        if (row.vat_rate or 0) > 0:
            # A taxed contract stays standard, and a stray 0% line under it is
            # zero-rated — exactly what the old rate-derived code emitted. Only
            # a contract that is itself untaxed can be outside the scope of tax.
            contract_category = "standard"
            item_zero_category = "zero_rated"
        else:
            contract_category = _zero_rate_category(row.country, cache)
            item_zero_category = contract_category

        conn.execute(
            sa.text('UPDATE contract SET "VAT_category" = :cat WHERE id = :id'),
            {"cat": contract_category, "id": row.id},
        )
        conn.execute(
            sa.text(
                'UPDATE invoiceitem SET "VAT_category" = '
                "CASE WHEN \"VAT_rate\" > 0 THEN 'standard' ELSE :zero END "
                "WHERE invoice_id IN "
                "(SELECT id FROM invoice WHERE contract_id = :id)"
            ),
            {"zero": item_zero_category, "id": row.id},
        )


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("contract", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "VAT_category",
                sa.Enum("standard", "zero_rated", "outside_scope", name="taxcategory"),
                server_default="standard",
                nullable=False,
            )
        )

    with op.batch_alter_table("invoiceitem", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "VAT_category",
                sa.Enum("standard", "zero_rated", "outside_scope", name="taxcategory"),
                server_default="standard",
                nullable=False,
            )
        )

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("tax_number", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )

    # ### end Alembic commands ###

    _backfill(op.get_bind())
    op.execute("PRAGMA foreign_key_check")


def downgrade() -> None:
    """Downgrades are not supported.

    Tuttle is a single-user desktop app. Rolling back schema is destructive
    (data in dropped columns is lost) and offers nothing over restoring a
    timestamped backup from ensure_schema()'s pre-upgrade snapshot.

    If you need to iterate on a migration during development:
    1. Delete this revision file (versions/5f919b074635_*.py)
    2. Run `just reset` to wipe ~/.tuttle
    3. Edit model.py, run `just migrate` again
    """
    raise NotImplementedError(
        "Downgrades are not supported. Restore from a .bak-<ts> snapshot instead."
    )
