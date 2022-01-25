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


def get_template_path(template_name) -> str:
    """Get the path to an HTML template by name"""
    module_path = Path(__file__).parent.resolve()
    template_path = module_path / Path(f"../templates/{template_name}")
    return template_path


def render_invoice(user: User, invoice: Invoice, out_dir: str = None) -> str:
    """Render an Invoice using an HTML template.

    Args:
        user (User): [description]
        invoice (Invoice): [description]

    Returns:
        str: [description]
    """
    template_name = "invoice"
    template_path = get_template_path(template_name)
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
    invoice_template = template_env.get_template(f"{template_name}.html")
    html = invoice_template.render(user=user, invoice=invoice)
    # output
    if out_dir is None:
        return html
    else:
        # write invoice html
        prefix = f"Invoice-{invoice.number}"
        invoice_dir = Path(out_dir) / Path(prefix)
        invoice_dir.mkdir(parents=True, exist_ok=True)
        invoice_path = invoice_dir / Path(f"{prefix}.html")
        with open(invoice_path, "w") as invoice_file:
            invoice_file.write(html)
        # copy stylsheet
        # stylesheet_path = template_path / f"{template_name}.css"
        # shutil.copy(stylesheet_path, invoice_dir)
