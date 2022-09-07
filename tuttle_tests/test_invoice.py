"""Tests for the invoice module."""

import datetime

from tuttle import invoicing, timetracking
from tuttle.model import Invoice, InvoiceItem


def test_invoice():
    the_invoice = Invoice(
        number="27B-6",
        date=datetime.date.today(),
        due_date=datetime.date.today() + datetime.timedelta(days=14),
        sent_date=datetime.date.today(),
        sent=True,
        paid="foo",
        cancelled=False,
    )

    item_1 = InvoiceItem(
        invoice=the_invoice,
        date=datetime.date.today(),
        quantity=10,
        unit="hours",
        unit_price=50,
        description="work work",
        VAT_rate=0.20,
    )

    item_2 = InvoiceItem(
        invoice=the_invoice,
        date=datetime.date.today(),
        quantity=10,
        unit="hours",
        unit_price=100,
        description="work work",
        VAT_rate=0.20,
    )

    assert the_invoice.sum == 1500
    assert the_invoice.VAT_total == 300
    assert the_invoice.total == 1800


def test_generate_invoice(
    demo_projects,
    demo_calendar_timetracking,
):
    for project in demo_projects:
        timesheets = []
        for period in ["January 2022", "February 2022"]:
            timesheet = timetracking.generate_timesheet(
                source=demo_calendar_timetracking,
                project=project,
                period_start=period,
                item_description=project.title,
            )
            if not timesheet.empty:
                timesheets.append(timesheet)
        invoice = invoicing.generate_invoice(
            timesheets=timesheets,
            contract=project.contract,
            date=datetime.date.today(),
        )
        assert invoice.total > 0


def test_render_invoice_to_html():
    pass


def test_render_invoice_to_pdf():
    pass
