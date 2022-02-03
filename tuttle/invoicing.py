"""Invoicing."""

from typing import List
import datetime
from pathlib import Path
import shutil


import pandas
import datetime

from .model import InvoiceItem, Invoice, Contract, User
from .timetracking import Timesheet


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
            VAT_rate=0.19,  # TODO: adjustable VAT rate
            description=timesheet.title,
        )
    invoice.generate_number()
    return invoice


def format_currency():
    raise NotImplementedError()
