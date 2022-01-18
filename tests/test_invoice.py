"""Tests for the invoice module."""

import datetime

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
        amount=10,
        unit="hours",
        unit_price=50,
        description="work work",
        VAT_rate=0.20,
    )

    item_2 = InvoiceItem(
        invoice=the_invoice,
        date=datetime.date.today(),
        amount=10,
        unit="hours",
        unit_price=100,
        description="work work",
        VAT_rate=0.20,
    )

    assert the_invoice.sum == 1500
    assert the_invoice.VAT_total == 300
    assert the_invoice.total == 1800
