"""Tests for recording invoice sent dates and timeline events."""

import datetime
from decimal import Decimal

import sqlmodel

from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.app.timeline.intent import TimelineIntent
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project
from tuttle.time import Cycle, TimeUnit


class _SavingDataSource:
    def __init__(self):
        self.saved = []

    def save_invoice(self, invoice):
        self.saved.append(invoice)


def _invoice() -> Invoice:
    client = Client(
        name="Central Services",
        address=Address(
            street="Main",
            number="1",
            postal_code="10000",
            city="Metro",
            country="BR",
        ),
    )
    contract = Contract(
        title="Heating",
        client=client,
        start_date=datetime.date(2026, 5, 1),
        rate=Decimal("100"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    project = Project(
        title="Radiator upgrade",
        description="Timeline test project",
        tag="#radiator",
        contract=contract,
        start_date=datetime.date(2026, 5, 1),
    )
    invoice = Invoice(
        number="2026-05-13-2",
        date=datetime.date(2026, 5, 13),
        contract=contract,
        project=project,
        sent=True,
        sent_date=datetime.date(2026, 5, 14),
        paid=False,
        cancelled=False,
    )
    invoice.items.append(
        InvoiceItem(
            invoice=invoice,
            quantity=1,
            unit="hour",
            unit_price=Decimal("100"),
            description="Work",
            VAT_rate=Decimal("0.19"),
        )
    )
    return invoice


def test_toggle_sent_sets_and_clears_sent_date():
    intent = InvoicingIntent.__new__(InvoicingIntent)
    intent._invoicing_data_source = _SavingDataSource()
    invoice = Invoice(number="1", date=datetime.date(2026, 5, 13), sent=False)

    result = intent.toggle_invoice_sent_status(invoice)

    assert result.was_intent_successful
    assert invoice.sent is True
    assert invoice.sent_date == datetime.date.today()

    result = intent.toggle_invoice_sent_status(invoice)

    assert result.was_intent_successful
    assert invoice.sent is False
    assert invoice.sent_date is None


def test_timeline_includes_regular_invoice_sent_event():
    engine = sqlmodel.create_engine("sqlite://", echo=False)
    sqlmodel.SQLModel.metadata.create_all(engine)
    invoice = _invoice()
    with sqlmodel.Session(engine) as session:
        session.add(invoice)
        session.commit()

    intent = TimelineIntent()
    intent.db_engine = engine
    result = intent.get_events(category_filter="invoice")

    assert result.was_intent_successful
    sent_events = [e for e in result.data if e.title == "Invoice 2026-05-13-2 sent"]
    assert len(sent_events) == 1
    assert sent_events[0].date == datetime.date(2026, 5, 14)
