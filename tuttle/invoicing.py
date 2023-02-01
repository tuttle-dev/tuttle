"""Invoicing."""

from typing import List, Optional, Dict
import datetime
from pathlib import Path
import shutil


import pandas
import datetime

from .model import InvoiceItem, Invoice, Contract, User, Project
from .timetracking import Timesheet


def generate_invoice(
    timesheets: List[Timesheet],
    contract: Contract,
    project: Project,
    date: datetime.date = datetime.date.today(),
    counter: int = None,
) -> Invoice:
    invoice = Invoice(
        date=date,
        contract=contract,
        project=project,
    )
    for timesheet in timesheets:
        total_hours = timesheet.total / pandas.Timedelta("1h")
        item = InvoiceItem(
            invoice=invoice,
            start_date=timesheet.table["begin"].min().date(),
            end_date=timesheet.table["end"].max().date(),
            quantity=total_hours,
            unit="hour",
            unit_price=timesheet.project.contract.rate,
            VAT_rate=contract.VAT_rate,
            description=timesheet.title,
        )

    # TODO: replace with auto-incrementing numbers
    invoice.generate_number(counter=counter)
    return invoice


def generate_invoice_email(
    invoice: Invoice,
    user: User,
) -> Dict:
    """Generate an email with the invoice attached."""
    body = f"""
    Dear {invoice.client.invoicing_contact.first_name}

    Please find attached the invoice number {invoice.number}.

    Best regards
    {user.name}
    """

    email = {
        "subject": f"Invoice {invoice.number}",
        "body": body,
        "recipient": invoice.client.invoicing_contact.email,
    }
    return email
