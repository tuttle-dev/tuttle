"""Invoicing."""

import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from .i18n import _
from .model import (
    Contract,
    ContractCharge,
    Invoice,
    InvoiceItem,
    PaymentMilestone,
    Project,
    User,
)
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
    project: Optional[Project] = None,
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
                project=project,
                project_id=project.id if project else None,
            )
        )
    return items


def _distinct_projects(projects) -> List[Project]:
    """Projects in first-seen order, without duplicates and without None."""
    seen: List[Project] = []
    for p in projects:
        if p is not None and not any(p is q or (p.id is not None and p.id == q.id) for q in seen):
            seen.append(p)
    return seen


def assign_invoice_project(invoice: Invoice) -> None:
    """Derive the invoice's project from its lines.

    All lines on one project: the invoice belongs to it. Lines on several
    projects: the invoice has no single project. No line with a project
    (lines older than #666): leave the invoice as it is.
    """
    projects = _distinct_projects(item.project for item in invoice.items)
    if len(projects) == 1:
        invoice.project = projects[0]
        invoice.project_id = projects[0].id
    elif len(projects) > 1:
        invoice.project = None
        invoice.project_id = None


def generate_invoice(
    timesheets: List[Timesheet],
    contract: Contract,
    project: Optional[Project],
    number: str,
    date: datetime.date = datetime.date.today(),
    charges: Optional[Sequence[ContractCharge]] = None,
) -> Invoice:
    """Bill timesheets of one contract; each may belong to a different project.

    Each timesheet becomes one line at its project's rate. With several
    projects, per-unit charges are split per project so each project's
    revenue adds up, and the invoice itself has no single project.
    """
    invoice = Invoice(
        date=date,
        contract=contract,
        contract_id=contract.id,
        project=project,
        project_id=project.id if project else None,
        number=number,
    )
    unit_td = contract.unit_duration
    vat_rate = _contract_vat_rate(contract)
    # per project: [billable quantity, first start, last end]
    totals: dict = {}
    for timesheet in timesheets:
        ts_project = timesheet.project or project
        # ``rate`` may be stored as float at runtime even though it is declared
        # ``condecimal``; effective_rate returns a Decimal so subtotals are exact.
        unit_price = ts_project.effective_rate if ts_project else Decimal(str(contract.rate))
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
            project=ts_project,
            project_id=ts_project.id if ts_project else None,
        )
        key = id(ts_project)
        total = totals.setdefault(key, [ts_project, Decimal("0"), item.start_date, item.end_date])
        total[1] += Decimal(str(quantity))
        total[2] = min(total[2], item.start_date)
        total[3] = max(total[3], item.end_date)
        invoice.items.append(item)

    # Charges follow the time lines, so an invoice reads "3 days worked,
    # 3 daily allowances" rather than interleaving the two.
    applicable = _applicable_charges(contract, charges)
    per_project = list(totals.values())
    if len(per_project) <= 1:
        p, quantity, start, end = per_project[0] if per_project else (project, None, None, None)
        invoice.items.extend(
            build_charge_items(
                applicable, contract=contract, billable_quantity=quantity, start_date=start, end_date=end, project=p
            )
        )
    else:
        period_start = min(t[2] for t in per_project)
        period_end = max(t[3] for t in per_project)
        for charge in applicable:
            if charge.basis == ChargeBasis.per_unit:
                for p, quantity, start, end in per_project:
                    for item in build_charge_items([charge], contract, quantity, start, end, project=p):
                        item.description = f"{p.title}: {item.description}"
                        invoice.items.append(item)
            else:
                # A flat fee is billed once; it is booked to the first project.
                first = per_project[0][0]
                invoice.items.extend(build_charge_items([charge], contract, None, period_start, period_end, project=first))

    assign_invoice_project(invoice)
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
        project=project,
        project_id=project.id,
    )
    invoice.items.append(item)
    # A fixed-price contract has no billable units, so per-unit charges are
    # rejected at validation and never reach here.
    invoice.items.extend(
        build_charge_items(
            _applicable_charges(contract, charges),
            contract=contract,
            project=project,
        )
    )
    return invoice


def milestone_amount(milestone: PaymentMilestone, contract: Contract) -> Decimal:
    """The net amount a milestone bills, resolved against the contract total.

    A milestone is expressed either as an absolute amount or as a percentage
    of the contract's fixed price. Percentages are quantized to cents, so a
    schedule of thirds bills 3,333.33 rather than a repeating fraction; the
    resulting rounding difference is absorbed by the final invoice, which
    deducts the deposits actually issued.
    """
    if milestone.amount is not None:
        return Decimal(str(milestone.amount)).quantize(Decimal("0.01"))
    if milestone.percentage is None:
        raise ValueError("Milestone must have either a percentage or an amount.")
    if contract.fixed_price is None:
        raise ValueError("Percentage milestones require a fixed-price contract.")
    total_price = Decimal(str(contract.fixed_price))
    share = total_price * Decimal(str(milestone.percentage)) / Decimal("100")
    return share.quantize(Decimal("0.01"))


def generate_deposit_invoice(
    contract: Contract,
    project: Project,
    milestone: PaymentMilestone,
    number: str,
    date: datetime.date = datetime.date.today(),
) -> Invoice:
    """Create a deposit invoice (Abschlagsrechnung) for a payment milestone.

    Contract charges are deliberately not billed here: a handling fee or setup
    cost belongs on the final settlement, not repeated on every instalment.
    """
    if contract.fixed_price is None:
        raise ValueError("Deposit invoices require a fixed-price contract.")

    invoice = Invoice(
        date=date,
        document_type="deposit",
        contract=contract,
        contract_id=contract.id,
        project=project,
        project_id=project.id,
        number=number,
        milestone_id=milestone.id,
    )
    item = InvoiceItem(
        quantity=1,
        unit="fixed_price",
        unit_price=milestone_amount(milestone, contract),
        VAT_rate=_contract_vat_rate(contract),
        VAT_category=contract.VAT_category,
        description=milestone.title,
        project=project,
        project_id=project.id,
    )
    invoice.items.append(item)
    return invoice


def generate_final_invoice(
    contract: Contract,
    project: Project,
    deposit_invoices: List[Invoice],
    number: str,
    date: datetime.date = datetime.date.today(),
    charges: Optional[Sequence[ContractCharge]] = None,
) -> Invoice:
    """Create a final invoice (Schlussrechnung) for a fixed-price contract.

    German tax law requires the Schlussrechnung to state the *full* contract
    amount with its VAT, then deduct the gross amounts already invoiced as
    deposits — so the line items here carry the whole fixed price, not the
    remainder. The deduction lines themselves come from the model's
    ``deposit_deductions``, and ``Invoice.remaining_balance`` is what the
    client actually owes.
    """
    if contract.fixed_price is None:
        raise ValueError("Final invoices require a fixed-price contract.")

    invoice = Invoice(
        date=date,
        document_type="final",
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
        project=project,
        project_id=project.id,
    )
    invoice.items.append(item)
    # Charges land on the settlement only — a per-invoice fee must not be
    # multiplied across the instalments of a single contract.
    invoice.items.extend(
        build_charge_items(
            _applicable_charges(contract, charges),
            contract=contract,
            project=project,
        )
    )

    for dep in deposit_invoices:
        dep.deposit_for_id = invoice.id

    invoice.deposits = deposit_invoices
    return invoice


def generate_invoice_email(
    invoice: Invoice,
    user: User,
) -> Optional[Dict]:
    """Email that sends an invoice or payment reminder, in the current document language.

    Returns None when no contact email is available.
    """
    client = invoice.client
    contact = client.invoice_recipient_contact if client else None
    recipient = contact.email if contact and contact.email else None
    if not recipient:
        return None

    values = {
        "name": contact.name if contact.name else client.name,
        "number": invoice.number,
        "project": invoice.project.title if invoice.project else "",
        "sender": user.name,
    }
    if not invoice.is_reminder:
        subject = _("Invoice {number}", **values)
        body = _(
            "Dear {name},\n\nPlease find attached the invoice for {project}.\n\nBest regards,\n{sender}",
            **values,
        )
    else:
        subject = _("Payment Reminder: Invoice {number}", **values)
        if invoice.reminder_level <= 1:
            body = _(
                "Dear {name},\n\n"
                "This is a reminder regarding the outstanding invoice {number} for {project}.\n\n"
                "Please find attached the payment reminder.\n\nBest regards,\n{sender}",
                **values,
            )
        elif invoice.reminder_level == 2:
            body = _(
                "Dear {name},\n\n"
                "This is a 2nd reminder regarding the outstanding invoice {number} for {project}.\n\n"
                "Please find attached the payment reminder.\n\nBest regards,\n{sender}",
                **values,
            )
        else:
            body = _(
                "Dear {name},\n\n"
                "This is a 3rd reminder regarding the outstanding invoice {number} for {project}.\n\n"
                "Please find attached the payment reminder.\n\nBest regards,\n{sender}",
                **values,
            )
    return {"subject": subject, "body": body, "recipient": recipient}
