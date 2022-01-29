"""Invoicing."""

from typing import List
import datetime
from pathlib import Path
import shutil


import pandas
import jinja2

from .model import InvoiceItem, Invoice, Contract, User
from .timetracking import Timesheet


def generate_invoice(
    timesheets: List[Timesheet],
    contract: Contract,
) -> Invoice:
    invoice = Invoice(
        date=datetime.date.today(),
        due_date=datetime.date.today(),
        sent_date=datetime.date.today(),
        contract=contract,
    )
    for timesheet in timesheets:
        total_hours = timesheet.total / pandas.Timedelta("1h")
        item = InvoiceItem(
            invoice=invoice,
            date=timesheet.table["end"].max(),
            quantity=total_hours,
            unit="hour",
            unit_price=timesheet.project.contract.rate,
            VAT_rate=0.19,
            description=timesheet.title,
        )
    invoice.generate_number()
    return invoice


def format_currency():
    raise NotImplementedError()
