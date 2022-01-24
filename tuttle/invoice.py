"""Invoicing."""

from typing import List
import datetime

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
            date=timesheet.table.index.max(),
            quantity=total_hours,
            unit="hour",
            unit_price=timesheet.project.contract.rate,
            VAT_rate=0.19,
        )
    invoice.generate_number()
    return invoice


def format_currency():
    raise NotImplementedError()


def render_invoice(
    user: User,
    invoice: Invoice,
):
    template_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("../../tuttle/templates/invoice")
    )
    invoice_template = template_env.get_template("invoice.html")

    html = invoice_template.render(user=user, invoice=invoice)
    return html
