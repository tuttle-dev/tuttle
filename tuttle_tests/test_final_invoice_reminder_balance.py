"""A reminder for a final invoice asks for what the deposits left, plus its fee.

The reminder repeats the final invoice's items, which state the full contract
price, so it must also repeat the deductions; otherwise the PDF and its payment
QR code ask the client for the whole price again.
"""

import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tuttle import invoicing, rendering
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.core.rpc_utils import dump
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.model import Address, BankAccount, Client, Contract, Invoice, PaymentMilestone, Project, User
from tuttle.time import ContractType, Cycle

DATE = datetime.date(2026, 2, 1)
TEMPLATES = sorted(p.parent.name for p in (Path(__file__).parent.parent / "templates").glob("invoice*/invoice.html"))

# 10,000 net at 19% VAT in instalments of 40%, 40% and 20%: two deposits of
# 4,760 gross leave 2,380 of the 11,900 for the final invoice.
FINAL_BALANCE = Decimal("2380.00")
FEE = Decimal("5.00")


def _user() -> User:
    return User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        email="mail@tuttle.example",
        VAT_number="27B-6",
        address=Address(street="Main Street", number="450", postal_code="55555", city="Sao Paolo", country="Brazil"),
        bank_accounts=[BankAccount(name="Harry Tuttle", IBAN="DE89370400440532013000", BIC="COBADEFFXXX")],
    )


def _contract() -> Contract:
    return Contract(
        term_of_payment=14,
        title="Central Heating Overhaul",
        client=Client(
            name="Sam Lowry",
            address=Address(street="Main Street", number="9999", postal_code="55555", city="Sao Paolo", country="Brazil"),
        ),
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


def _ok(result):
    assert result.was_intent_successful, result.error_msg
    return result.data


@pytest.fixture
def settlement(monkeypatch) -> tuple[InvoicingIntent, list[Invoice], Invoice]:
    """Two deposits and the final invoice that settles them, all unpaid."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    with Session(engine) as session:
        session.add(_user())
        project = Project(
            title="Heating Overhaul",
            description="Ductwork",
            tag="#overhaul",
            contract=_contract(),
            start_date=datetime.date(2026, 1, 10),
        )
        session.add(project)
        session.commit()
        project_id, milestone_ids = project.id, [m.id for m in project.contract.payment_milestones]

    intent = InvoicingIntent()
    deposits = [_ok(intent.create_deposit(project_id, milestone_id, DATE)) for milestone_id in milestone_ids[:2]]
    final = _ok(intent.create_final(project_id, DATE))
    return intent, deposits, final


def _load(intent: InvoicingIntent, invoice: Invoice) -> Invoice:
    return _ok(intent._invoicing_data_source.get_invoice_by_id(invoice.id))


def _remind(intent: InvoicingIntent, invoice: Invoice, fee=FEE) -> Invoice:
    _ok(intent.toggle_sent(invoice.id))
    reminder = _ok(intent.create_reminder(invoice.id, "2026-08-01", "2026-08-15", str(fee)))
    return _load(intent, reminder)


class TestReminderForAFinalInvoice:
    def test_restates_the_deductions_of_the_final_invoice(self, settlement):
        intent, _, final = settlement
        reminder = _remind(intent, final)

        assert reminder.deposit_deductions == _load(intent, final).deposit_deductions
        assert len(reminder.deposit_deductions) == 2

    def test_asks_for_the_remaining_balance_plus_the_fee(self, settlement):
        intent, _, final = settlement
        reminder = _remind(intent, final)

        assert reminder.total == Decimal("11905.00")
        assert reminder.remaining_balance == FINAL_BALANCE + FEE

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_its_pdf_deducts_the_deposits_before_adding_the_fee(self, settlement, template):
        intent, deposits, final = settlement
        reminder = _remind(intent, final)

        html = rendering.render_invoice(user=_user(), invoice=reminder, out_dir=None, template_name=template)

        assert "€2,385.00" in html
        assert "€11,905.00" not in html
        assert "€11,900.00" in html  # the gross amount the deposits are deducted from
        for deposit in deposits:
            assert f"less deposit per invoice no. {deposit.number}" in html
        assert html.index("Reminder Fee") > html.rindex("less deposit per invoice no.")

    def test_its_payment_qr_code_asks_for_the_same_amount(self, settlement, monkeypatch):
        intent, _, final = settlement
        reminder = _remind(intent, final)
        amounts = []
        make_epc_qr = rendering.make_epc_qr
        monkeypatch.setattr(rendering, "make_epc_qr", lambda **kw: amounts.append(kw["amount"]) or make_epc_qr(**kw))

        assert rendering.generate_payment_qr(_user().bank_account, _load(intent, final)) is not None
        assert rendering.generate_payment_qr(_user().bank_account, reminder) is not None

        assert amounts == [float(FINAL_BALANCE), float(FINAL_BALANCE + FEE)]

    def test_a_second_reminder_restates_it_too(self, settlement):
        intent, _, final = settlement
        first = _remind(intent, final)
        second = _remind(intent, first, fee=Decimal("10.00"))

        assert second.reminder_chain_head_id == final.id
        assert second.remaining_balance == FINAL_BALANCE + Decimal("10.00")
        served = {inv["id"]: inv for inv in dump(_ok(intent.get_all()))}
        assert served[second.id]["remaining_balance"] == float(FINAL_BALANCE + Decimal("10.00"))

    def test_paid_settles_the_deposits_too(self, settlement):
        intent, deposits, final = settlement
        reminder = _remind(intent, final)

        _ok(intent.toggle_paid(reminder.id))

        assert [_load(intent, inv).paid for inv in (reminder, final, *deposits)] == [True] * 4


def test_a_reminder_for_an_ordinary_invoice_asks_for_its_total(settlement):
    intent, (deposit, _), _ = settlement
    reminder = _remind(intent, deposit)

    assert reminder.deposit_deductions == []
    assert reminder.remaining_balance == reminder.total == Decimal("4765.00")


def test_a_settled_final_invoice_gets_no_payment_qr_code():
    """Nothing is due once the deposits cover the whole price."""
    project = Project(title="Heating Overhaul", description="", tag="#overhaul", contract=_contract())
    contract = project.contract
    deposits = [
        invoicing.generate_deposit_invoice(contract, project, milestone, number=f"2026-0{position}", date=DATE)
        for position, milestone in enumerate(contract.payment_milestones)
    ]
    final = invoicing.generate_final_invoice(contract, project, deposits, number="2026-09", date=DATE)

    assert final.remaining_balance == 0
    assert rendering.generate_payment_qr(_user().bank_account, final) is None
