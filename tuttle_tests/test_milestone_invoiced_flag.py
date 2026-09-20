"""A milestone is billable again once the document that invoiced it is void.

``PaymentMilestone.invoiced`` gates the deposit-invoice dropdown. It must
follow the live invoices: a deposit that is cancelled or deleted never charged
its instalment, and a voided final invoice settles nothing.
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


def _schedule(engine, *percentages: str) -> tuple[int, list[int]]:
    """Persist a fixed-price project with one milestone per percentage."""
    with Session(engine) as session:
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
            title="Central Heating Overhaul",
            client=Client(
                name="Sam Lowry",
                address=Address(street="Shangrila Towers", number="1", postal_code="00000", city="Brazil", country="Germany"),
            ),
            start_date=datetime.date(2026, 1, 10),
            type=ContractType.fixed_price,
            fixed_price=Decimal("10000"),
            currency="EUR",
            VAT_rate=Decimal("0.19"),
            billing_cycle=Cycle.monthly,
            payment_milestones=[
                PaymentMilestone(title=f"Instalment {position + 1}", percentage=Decimal(pct), position=position)
                for position, pct in enumerate(percentages)
            ],
        )
        project = Project(
            title="Heating Overhaul",
            description="Ductwork",
            tag="#deposit",
            contract=contract,
            start_date=datetime.date(2026, 1, 10),
            end_date=datetime.date(2026, 6, 30),
        )
        session.add(project)
        session.commit()
        return project.id, [m.id for m in contract.payment_milestones]


def _invoiced(engine, milestone_ids: list[int]) -> list[bool]:
    with Session(engine) as session:
        return [session.get(PaymentMilestone, mid).invoiced for mid in milestone_ids]


def _deposit(intent: InvoicingIntent, project_id: int, milestone_id: int) -> Invoice:
    result = intent.create_deposit(project_id, milestone_id, DATE)
    assert result.was_intent_successful, result.error_msg
    return result.data


def _final(intent: InvoicingIntent, project_id: int) -> Invoice:
    result = intent.create_final(project_id, DATE)
    assert result.was_intent_successful, result.error_msg
    return result.data


class TestDepositInvoice:
    def test_issuing_a_deposit_closes_its_milestone(self, in_memory_db):
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        _deposit(InvoicingIntent(), project_id, first)
        assert _invoiced(in_memory_db, [first, second, third]) == [True, False, False]

    def test_cancelling_the_deposit_reopens_the_milestone(self, in_memory_db):
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        deposit = _deposit(intent, project_id, first)

        assert intent.toggle_cancelled(deposit.id).was_intent_successful
        assert _invoiced(in_memory_db, [first, second, third]) == [False, False, False]

    def test_a_reopened_milestone_can_be_invoiced_again(self, in_memory_db):
        """The reported bug: cancel a deposit, and the schedule stayed closed."""
        project_id, (first, *_) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        deposit = _deposit(intent, project_id, first)
        intent.toggle_cancelled(deposit.id)

        replacement = _deposit(intent, project_id, first)
        assert replacement.id != deposit.id
        assert _invoiced(in_memory_db, [first]) == [True]

    def test_reinstating_the_deposit_closes_the_milestone_again(self, in_memory_db):
        project_id, (first, *_) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        deposit = _deposit(intent, project_id, first)
        intent.toggle_cancelled(deposit.id)

        intent.toggle_cancelled(deposit.id)
        assert _invoiced(in_memory_db, [first]) == [True]

    def test_deleting_the_deposit_reopens_the_milestone(self, in_memory_db):
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        deposit = _deposit(intent, project_id, first)

        assert intent.delete_invoice_by_id(deposit.id).was_intent_successful
        assert _invoiced(in_memory_db, [first, second, third]) == [False, False, False]

        _deposit(intent, project_id, first)
        assert _invoiced(in_memory_db, [first, second, third]) == [True, False, False]

    def test_other_milestones_keep_their_own_state(self, in_memory_db):
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        _deposit(intent, project_id, first)
        second_deposit = _deposit(intent, project_id, second)

        intent.toggle_cancelled(second_deposit.id)
        assert _invoiced(in_memory_db, [first, second, third]) == [True, False, False]


class TestFinalInvoice:
    def test_the_settlement_closes_every_remaining_milestone(self, in_memory_db):
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        _deposit(intent, project_id, first)
        _final(intent, project_id)
        assert _invoiced(in_memory_db, [first, second, third]) == [True, True, True]

    def test_cancelling_the_settlement_reopens_only_what_it_covered(self, in_memory_db):
        """A milestone with its own live deposit stays invoiced."""
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        _deposit(intent, project_id, first)
        final = _final(intent, project_id)

        intent.toggle_cancelled(final.id)
        assert _invoiced(in_memory_db, [first, second, third]) == [True, False, False]

    def test_a_cancelled_settlement_can_be_issued_again(self, in_memory_db):
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        deposit = _deposit(intent, project_id, first)
        final = _final(intent, project_id)
        intent.toggle_cancelled(final.id)

        replacement = _final(intent, project_id)
        assert replacement.id != final.id
        assert _invoiced(in_memory_db, [first, second, third]) == [True, True, True]
        with Session(in_memory_db) as session:
            assert session.get(Invoice, deposit.id).deposit_for_id == replacement.id

    def test_deleting_the_settlement_reopens_only_what_it_covered(self, in_memory_db):
        project_id, (first, second, third) = _schedule(in_memory_db, "40", "30", "30")
        intent = InvoicingIntent()
        deposit = _deposit(intent, project_id, first)
        final = _final(intent, project_id)

        assert intent.delete_invoice_by_id(final.id).was_intent_successful
        assert _invoiced(in_memory_db, [first, second, third]) == [True, False, False]
        with Session(in_memory_db) as session:
            assert session.get(Invoice, deposit.id).deposit_for_id is None

    def test_the_last_open_milestone_is_settled_and_reopens_on_cancel(self, in_memory_db):
        """Invoicing the last instalment issues the final invoice instead."""
        project_id, (first, second) = _schedule(in_memory_db, "50", "50")
        intent = InvoicingIntent()
        _deposit(intent, project_id, first)
        final = _deposit(intent, project_id, second)
        assert final.is_final_invoice
        assert _invoiced(in_memory_db, [first, second]) == [True, True]

        intent.toggle_cancelled(final.id)
        assert _invoiced(in_memory_db, [first, second]) == [True, False]
