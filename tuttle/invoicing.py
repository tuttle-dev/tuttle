"""Invoicing."""

from typing import List
import datetime
from pathlib import Path
import shutil
from venv import create


import pandas
import datetime

from .model import InvoiceItem, Invoice, Contract, User
from .timetracking import Timesheet
from .mail import create_email, send_email


def generate_invoice(
    timesheets: List[Timesheet],
    contract: Contract,
    date: datetime.date = datetime.date.today(),
) -> Invoice:
    invoice = Invoice(
        date=date,
        contract=contract,
    )
    for timesheet in timesheets:
        total_hours = timesheet.total / pandas.Timedelta("1h")
        item = InvoiceItem(
            invoice=invoice,
            date=date,
            quantity=total_hours,
            unit="hour",
            unit_price=timesheet.project.contract.rate,
            VAT_rate=contract.VAT_rate,
            description=timesheet.title,
        )
    invoice.generate_number()
    return invoice


def send_invoice(
    user: User,
    invoice: Invoice,
):
    message = create_email(
        email_from=user.email,
        email_to=invoice.client,
        subject=invoice.number,
        body=None,  #
        attachments=None,  # TODO: inovice as PDF
    )
