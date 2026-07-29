"""Invoicing."""

import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from .model import Contract, ContractCharge, Invoice, InvoiceItem, Project, User
from .time import ChargeBasis
from .timetracking import Timesheet


def _contract_vat_rate(contract: Contract) -> Decimal:
    """VAT rate of a contract as a fraction.

    Defensive: VAT_rate is stored as a fraction (0.19 = 19%). Some legacy /
    LLM-imported contracts persisted percent values directly (e.g. 19 or 1900),
    which previously produced absurd VAT totals like 1900%. Normalize any
    value > 1 back into a fraction.
    """
    vat_rate = Decimal(str(contract.VAT_rate))
    while vat_rate > Decimal("1"):
        vat_rate = vat_rate / Decimal("100")
    return vat_rate


def _applicable_charges(
    contract: Contract,
    charges: Optional[Sequence[ContractCharge]],
) -> List[ContractCharge]:
    """Resolve which contract charges to bill on this invoice.

    An explicit *charges* sequence — as supplied by ``InvoicingIntent``,
    which can query the database — is taken as given. Without one, ``once``
    charges are left out: whether one has already been billed can only be
    answered by looking at earlier invoices, and silently omitting a
    one-time fee is far less damaging than silently billing it twice.
    """
    if charges is not None:
        return sorted(charges, key=lambda c: (c.position, c.id or 0))
    return sorted(
        (c for c in contract.charges if c.is_active and c.basis != ChargeBasis.once),
        key=lambda c: (c.position, c.id or 0),
    )


def build_charge_items(
    charges: Sequence[ContractCharge],
    contract: Contract,
    billable_quantity: Optional[Decimal] = None,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
) -> List[InvoiceItem]:
    """Turn contract charges into invoice lines.

    A ``per_unit`` charge mirrors *billable_quantity* — three billed days of
    work carry three daily fees — so it is skipped when there is no billable
    quantity to mirror. The flat bases are billed once at quantity 1.
    """
    vat_rate = _contract_vat_rate(contract)
    items: List[InvoiceItem] = []
    for charge in charges:
        if charge.basis == ChargeBasis.per_unit:
            if billable_quantity is None:
                continue
            quantity = float(billable_quantity)
        else:
            quantity = 1.0
        items.append(
            InvoiceItem(
                start_date=start_date,
                end_date=end_date,
                quantity=quantity,
                unit=charge.effective_unit(contract),
                unit_price=Decimal(str(charge.amount)),
                VAT_rate=vat_rate,
                VAT_category=contract.VAT_category,
                description=charge.description,
                contract_charge=charge,
                contract_charge_id=charge.id,
            )
        )
    return items


def generate_invoice(
    timesheets: List[Timesheet],
    contract: Contract,
    project: Project,
    number: str,
    date: datetime.date = datetime.date.today(),
    charges: Optional[Sequence[ContractCharge]] = None,
) -> Invoice:
    invoice = Invoice(
        date=date,
        contract=contract,
        contract_id=contract.id,
        project=project,
        project_id=project.id,
        number=number,
    )
    unit_td = contract.unit_duration
    # ``Contract.rate`` may be stored as float at runtime even though it is
    # declared ``condecimal`` — coerce here so ``InvoiceItem.subtotal`` always
    # multiplies two Decimals and the invoice totals are exact.
    unit_price = Decimal(str(contract.rate))
    vat_rate = _contract_vat_rate(contract)
    total_quantity = Decimal("0")
    period_start: Optional[datetime.date] = None
    period_end: Optional[datetime.date] = None
    for timesheet in timesheets:
        quantity = timesheet.total / unit_td
        total_quantity += Decimal(str(quantity))
        item = InvoiceItem(
            start_date=timesheet.table["begin"].min().date(),
            end_date=timesheet.table["end"].max().date(),
            quantity=quantity,
            unit=contract.unit.value,
            unit_price=unit_price,
            VAT_rate=vat_rate,
            VAT_category=contract.VAT_category,
            description=timesheet.title,
        )
        period_start = item.start_date if period_start is None else min(period_start, item.start_date)
        period_end = item.end_date if period_end is None else max(period_end, item.end_date)
        invoice.items.append(item)

    # Charges follow the time lines, so an invoice reads "3 days worked,
    # 3 daily allowances" rather than interleaving the two.
    invoice.items.extend(
        build_charge_items(
            _applicable_charges(contract, charges),
            contract=contract,
            billable_quantity=total_quantity,
            start_date=period_start,
            end_date=period_end,
        )
    )

    return invoice


def generate_fixed_price_invoice(
    contract: Contract,
    project: Project,
    number: str,
    date: datetime.date = datetime.date.today(),
    charges: Optional[Sequence[ContractCharge]] = None,
) -> Invoice:
    """Create a lump-sum invoice for a fixed-price contract (no timesheets)."""
    invoice = Invoice(
        date=date,
        contract=contract,
        contract_id=contract.id,
        project=project,
        project_id=project.id,
        number=number,
    )
    item = InvoiceItem(
        quantity=1,
        unit="fixed_price",
        unit_price=Decimal(str(contract.fixed_price)),
        VAT_rate=_contract_vat_rate(contract),
        VAT_category=contract.VAT_category,
        description=contract.title,
    )
    invoice.items.append(item)
    # A fixed-price contract has no billable units, so per-unit charges are
    # rejected at validation and never reach here.
    invoice.items.extend(
        build_charge_items(
            _applicable_charges(contract, charges),
            contract=contract,
        )
    )
    return invoice


def generate_invoice_email(
    invoice: Invoice,
    user: User,
) -> Optional[Dict]:
    """Generate an email with the invoice attached.

    Returns None when no contact email is available.
    """
    client = invoice.client
    contact = client.invoicing_contact if client else None
    greeting = contact.first_name if contact and contact.first_name else client.name
    recipient = contact.email if contact and contact.email else None

    if not recipient:
        return None

    body = f"""
    Dear {greeting}

    Please find attached the invoice number {invoice.number}.

    Best regards
    {user.name}
    """

    email = {
        "subject": f"Invoice {invoice.number}",
        "body": body,
        "recipient": recipient,
    }
    return email
