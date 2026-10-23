"""A deposit stays live while a final invoice settles it.

The final invoice deducts each of its deposits. A deposit cancelled behind its
back would still be deducted, so the client would be billed too little, and
revenue would lose the deposit's amount.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.model import Address, Client, Contract, Invoice, PaymentMilestone, Project, User
from tuttle.time import ContractType, Cycle

DATE = datetime.date(2026, 2, 1)


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _ok(result):
    assert result.was_intent_successful, result.error_msg
    return result.data


@pytest.fixture
def settlement(in_memory_db) -> tuple[InvoicingIntent, list[Invoice], Invoice]:
    """Two 40% deposits and the final invoice that settles them on 10,000 net."""
    with Session(in_memory_db) as session:
        # Rendering the PDF after creation reads the user's preferences.
        session.add(
            User(
                name="Harry Tuttle",
                subtitle="Heating Engineer",
                email="mail@tuttle.example",
                address=Address(street="Main Street", number="450", postal_code="55555", city="Sao Paolo", country="Brazil"),
            )
        )
        contract = Contract(
            term_of_payment=14,
            title="Central Heating Overhaul",
            client=Client(name="Sam Lowry"),
            start_date=datetime.date(2026, 1, 10),
            type=ContractType.fixed_price,
            fixed_price=Decimal("10000"),
            currency="EUR",
            VAT_rate=Decimal("0.19"),
            billing_cycle=Cycle.monthly,
            payment_milestones=[
                PaymentMilestone(title=f"Instalment {position + 1}", percentage=Decimal(pct), position=position)
                for position, pct in enumerate(("40", "40", "20"))
            ],
        )
        project = Project(
            title="Heating Overhaul",
            description="Ductwork",
            tag="#overhaul",
            contract=contract,
            start_date=datetime.date(2026, 1, 10),
        )
        session.add(project)
        session.commit()
        project_id, milestone_ids = project.id, [m.id for m in contract.payment_milestones]

    intent = InvoicingIntent()
    deposits = [_ok(intent.create_deposit(project_id, milestone_id, DATE)) for milestone_id in milestone_ids[:2]]
    final = _ok(intent.create_final(project_id, DATE))
    return intent, deposits, final


def _load(intent: InvoicingIntent, invoice: Invoice) -> Invoice:
    return _ok(intent._invoicing_data_source.get_invoice_by_id(invoice.id))


def _cancel_behind_the_final(engine, deposit: Invoice) -> None:
    """The state an older version left behind when a settled deposit was cancelled."""
    with Session(engine) as session:
        row = session.get(Invoice, deposit.id)
        row.cancelled = True
        session.add(row)
        session.commit()


class TestCancellingASettledDeposit:
    def test_is_refused_until_the_final_invoice_is_cancelled(self, settlement):
        intent, (deposit, _), final = settlement

        result = intent.toggle_cancelled(deposit.id)

        assert not result.was_intent_successful
        assert result.error_msg == (
            f"Deposit invoice {deposit.number} is settled by final invoice {final.number}. "
            "Cancel the final invoice first, then the deposit."
        )
        assert not _load(intent, deposit).cancelled
        # 11,900 gross less two deposits of 4,760.
        assert _load(intent, final).remaining_balance == Decimal("2380.00")

    def test_is_allowed_once_the_final_invoice_is_cancelled(self, settlement):
        intent, (deposit, _), final = settlement
        _ok(intent.toggle_cancelled(final.id))

        _ok(intent.toggle_cancelled(deposit.id))

        assert _load(intent, deposit).cancelled

    def test_restoring_a_cancelled_deposit_is_allowed(self, in_memory_db, settlement):
        intent, (deposit, _), _final = settlement
        _cancel_behind_the_final(in_memory_db, deposit)

        _ok(intent.toggle_cancelled(deposit.id))

        assert not _load(intent, deposit).cancelled


class TestPayingTheFinalInvoice:
    def test_marks_its_deposits_paid(self, settlement):
        intent, deposits, final = settlement

        _ok(intent.toggle_paid(final.id))

        assert [_load(intent, d).paid for d in deposits] == [True, True]

    def test_leaves_a_cancelled_deposit_unpaid(self, in_memory_db, settlement):
        intent, (cancelled, live), final = settlement
        _cancel_behind_the_final(in_memory_db, cancelled)

        _ok(intent.toggle_paid(final.id))

        assert not _load(intent, cancelled).paid
        assert _load(intent, live).paid


@pytest.mark.parametrize("toggle", ["toggle_sent", "toggle_paid", "toggle_cancelled"])
def test_a_failed_status_change_says_where_the_details_are(settlement, monkeypatch, toggle):
    """The invoice view shows the message, so it must not be a raw exception."""
    intent, _, final = settlement

    def broken_save(invoice):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(intent._invoicing_data_source, "save_invoice", broken_save)
    result = getattr(intent, toggle)(final.id)

    assert not result.was_intent_successful
    assert "unexpected error. Details are in the application log." in result.error_msg
    assert "database is locked" not in result.error_msg
