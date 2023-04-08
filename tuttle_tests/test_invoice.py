"""Tests for the invoice module."""

import datetime
from decimal import Decimal
from pathlib import Path

from tuttle import invoicing, timetracking, rendering
from tuttle.model import Invoice, InvoiceItem
from tuttle.calendar import get_month_start_end


def test_invoice():
    the_invoice = Invoice(
        number="27B-6",
        date=datetime.date.today(),
        sent=True,
        paid=False,
        cancelled=False,
    )

    item_1 = InvoiceItem(
        invoice=the_invoice,
        start_date=datetime.date.today(),
        end_date=datetime.date.today(),
        quantity=10,
        unit="hours",
        unit_price=Decimal(50),
        description="work work",
        VAT_rate=Decimal(0.20),
    )

    item_2 = InvoiceItem(
        invoice=the_invoice,
        start_date=datetime.date.today(),
        end_date=datetime.date.today(),
        quantity=10,
        unit="hours",
        unit_price=Decimal(100),
        description="work work",
        VAT_rate=Decimal(0.20),
    )

    assert item_1.invoice == the_invoice
    assert item_2.invoice == the_invoice

    assert the_invoice.sum == Decimal(1500)
    assert the_invoice.VAT_total == Decimal(300)
    assert the_invoice.total == Decimal(1800)


def test_generate_invoice(
    demo_projects,
    demo_calendar_timetracking,
):
    for i, project in enumerate(demo_projects):
        timesheets = []
        for period in ["January 2022", "February 2022"]:
            (period_start, period_end) = get_month_start_end(period)
            timesheet = timetracking.generate_timesheet(
                timetracking_data=demo_calendar_timetracking.to_data(),
                project=project,
                period_start=period_start,
                period_end=period_end,
                item_description=project.title,
            )
            if not timesheet.empty:
                timesheets.append(timesheet)
        invoice = invoicing.generate_invoice(
            timesheets=timesheets,
            contract=project.contract,
            project=project,
            date=datetime.date.today(),
            number=f"{datetime.date.today().strftime('%Y-%m-%d')}-{i}",
        )
        # assert invoice.total > 0
