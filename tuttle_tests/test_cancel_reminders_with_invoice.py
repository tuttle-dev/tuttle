"""A reminder chain shares the cancelled state of the invoice it chases.

A cancelled invoice is owed no more, so its reminders must not stay overdue,
and no new reminder may chase it. A single reminder can still be withdrawn.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.model import Address, Client, Contract, Invoice, Project, User
from tuttle.time import ContractType, Cycle

DATE = datetime.date(2026, 2, 1)


def _ok(result):
    assert result.was_intent_successful, result.error_msg
    return result.data


@pytest.fixture
def chain(monkeypatch) -> tuple[InvoicingIntent, Invoice, Invoice, Invoice]:
    """An invoice with a first and a second reminder."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    with Session(engine) as session:
        # Rendering the PDF after creation reads the user's preferences.
        session.add(
            User(
                name="Harry Tuttle",
                subtitle="Heating Engineer",
                email="mail@tuttle.example",
                operating_country="Germany",
                address=Address(street="Main Street", number="450", postal_code="55555", city="Sao Paolo", country="Brazil"),
            )
        )
        project = Project(
            title="Boiler Repair",
            description="Burner",
            tag="#boiler",
            start_date=datetime.date(2026, 1, 10),
            contract=Contract(
                VAT_rate=Decimal("0.19"),
                term_of_payment=14,
                title="Boiler Repair",
                client=Client(name="Sam Lowry"),
                start_date=datetime.date(2026, 1, 10),
                type=ContractType.fixed_price,
                fixed_price=Decimal("800"),
                currency="EUR",
                billing_cycle=Cycle.monthly,
            ),
        )
        session.add(project)
        session.commit()
        project_id = project.id

    intent = InvoicingIntent()
    invoice = _ok(intent.create(project_id, DATE, DATE, DATE))
    _ok(intent.toggle_sent(invoice.id))
    first = _ok(intent.create_reminder(invoice.id, "2026-03-01", "2026-03-15", "5.00"))
    _ok(intent.toggle_sent(first.id))
    second = _ok(intent.create_reminder(first.id, "2026-04-01", "2026-04-15", "10.00"))
    return intent, invoice, first, second


def _cancelled(intent: InvoicingIntent, *invoices: Invoice) -> list[bool]:
    return [_ok(intent._invoicing_data_source.get_invoice_by_id(inv.id)).cancelled for inv in invoices]


class TestCancellingTheInvoice:
    def test_cancels_its_reminders(self, chain):
        intent, invoice, first, second = chain

        _ok(intent.toggle_cancelled(invoice.id))

        assert _cancelled(intent, invoice, first, second) == [True, True, True]

    def test_restoring_it_restores_its_reminders(self, chain):
        intent, invoice, first, second = chain
        _ok(intent.toggle_cancelled(invoice.id))

        _ok(intent.toggle_cancelled(invoice.id))

        assert _cancelled(intent, invoice, first, second) == [False, False, False]


class TestCancellingAReminder:
    def test_cancels_only_that_reminder(self, chain):
        intent, invoice, first, second = chain

        _ok(intent.toggle_cancelled(first.id))

        assert _cancelled(intent, invoice, first, second) == [False, True, False]

    def test_it_can_be_restored_while_the_invoice_stands(self, chain):
        intent, invoice, first, second = chain
        _ok(intent.toggle_cancelled(first.id))

        _ok(intent.toggle_cancelled(first.id))

        assert _cancelled(intent, invoice, first, second) == [False, False, False]

    def test_it_cannot_be_restored_while_the_invoice_is_cancelled(self, chain):
        intent, invoice, first, second = chain
        _ok(intent.toggle_cancelled(invoice.id))

        result = intent.toggle_cancelled(first.id)

        assert not result.was_intent_successful
        assert result.error_msg == f"Invoice {invoice.number} is cancelled. Restore the invoice to restore its reminders."
        assert _cancelled(intent, first) == [True]


class TestNewReminder:
    def test_is_refused_for_a_cancelled_invoice_even_from_a_live_reminder(self, chain):
        """Reminders that an older version left live when it cancelled their invoice."""
        intent, invoice, first, second = chain
        invoice_row = _ok(intent._invoicing_data_source.get_invoice_by_id(invoice.id))
        invoice_row.cancelled = True
        intent._invoicing_data_source.save_invoice(invoice_row)

        result = intent.create_reminder(second.id, "2026-05-01", "2026-05-15")

        assert not result.was_intent_successful
        assert result.error_msg == f"Invoice {invoice.number} is cancelled. Restore it first if the client still owes it."

    def test_is_allowed_again_once_the_invoice_is_restored(self, chain):
        intent, invoice, first, second = chain
        _ok(intent.toggle_cancelled(invoice.id))
        _ok(intent.toggle_cancelled(invoice.id))

        third = _ok(intent.create_reminder(second.id, "2026-05-01", "2026-05-15"))

        assert third.reminder_level == 3
