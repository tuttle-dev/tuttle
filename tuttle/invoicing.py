"""Invoicing."""

from typing import List, Optional, Dict
import datetime
from decimal import Decimal

from .model import InvoiceItem, Invoice, Contract, User, Project
from .timetracking import Timesheet


def generate_invoice(
    timesheets: List[Timesheet],
    contract: Contract,
    project: Project,
    number: str,
    date: datetime.date = datetime.date.today(),
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
    vat_rate = Decimal(str(contract.VAT_rate))
    # Defensive: VAT_rate is stored as a fraction (0.19 = 19%). Some legacy /
    # LLM-imported contracts persisted percent values directly (e.g. 19 or 1900),
    # which previously produced absurd VAT totals like 1900%. Normalize any
    # value > 1 back into a fraction.
    while vat_rate > Decimal("1"):
        vat_rate = vat_rate / Decimal("100")
    for timesheet in timesheets:
        quantity = timesheet.total / unit_td
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
        invoice.items.append(item)

    return invoice


def generate_fixed_price_invoice(
    contract: Contract,
    project: Project,
    number: str,
    date: datetime.date = datetime.date.today(),
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
    vat_rate = Decimal(str(contract.VAT_rate))
    while vat_rate > Decimal("1"):
        vat_rate = vat_rate / Decimal("100")
    item = InvoiceItem(
        quantity=1,
        unit="fixed_price",
        unit_price=Decimal(str(contract.fixed_price)),
        VAT_rate=vat_rate,
        VAT_category=contract.VAT_category,
        description=contract.title,
    )
    invoice.items.append(item)
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
