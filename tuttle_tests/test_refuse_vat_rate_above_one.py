"""A stored VAT rate outside 0–1 is refused at invoice time, not rescaled.

Contracts store the rate as a fraction (0.19 is 19%). Invoicing used to divide
a larger value by 100 until it fitted, so a stored 1.9 billed 1.9% and 19
billed 19%: a guess at what was meant, printed on a legal document.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle import invoicing
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.model import Address, Client, Contract, ContractCharge, Invoice, PaymentMilestone, Project, User
from tuttle.time import ChargeBasis, ContractType, TimeUnit

DATE = datetime.date(2026, 2, 1)


def _contract(vat_rate, **kwargs) -> Contract:
    fields = dict(
        title="Heating",
        client=Client(
            name="Sam Lowry",
            address=Address(street="Shangrila Towers", number="1", postal_code="55555", city="Metro", country="Brazil"),
        ),
        start_date=datetime.date(2026, 1, 1),
        term_of_payment=14,
        currency="EUR",
        VAT_rate=Decimal(vat_rate),
        type=ContractType.time_based,
        rate=Decimal("100"),
        unit=TimeUnit.hour,
    )
    fields.update(kwargs)
    return Contract(**fields)


def _fixed_price(vat_rate) -> Contract:
    return _contract(vat_rate, type=ContractType.fixed_price, rate=None, fixed_price=Decimal("10000"))


def _project(contract: Contract) -> Project:
    return Project(
        title="Heating Repair", description="Ductwork", tag="#heating", contract=contract, start_date=datetime.date(2026, 1, 1)
    )


class TestBillableVatRate:
    @pytest.mark.parametrize(
        "stored, shown",
        [("1.9", "190"), ("19", "1900"), ("190", "19000"), ("-0.19", "-19")],
    )
    def test_a_rate_outside_0_to_1_is_refused_with_what_is_stored(self, stored, shown):
        with pytest.raises(ValueError) as excinfo:
            _contract(stored).billable_vat_rate()
        assert str(excinfo.value) == f"The VAT rate of contract “Heating” is {shown}%. Correct it, then create the invoice."

    @pytest.mark.parametrize("stored", ["0", "0.07", "0.19", "1"])
    def test_a_fraction_is_billed_as_stored(self, stored):
        assert _contract(stored).billable_vat_rate() == Decimal(stored)


class TestInvoiceGeneration:
    """Every invoice kind reads the rate through the same refusal."""

    def test_time_based(self):
        contract = _contract("1.9")
        with pytest.raises(ValueError, match="190%"):
            invoicing.generate_invoice([], contract, _project(contract), number="2026-001", date=DATE)

    def test_fixed_price(self):
        contract = _fixed_price("1.9")
        with pytest.raises(ValueError, match="190%"):
            invoicing.generate_fixed_price_invoice(contract, _project(contract), number="2026-001", date=DATE)

    def test_deposit(self):
        contract = _fixed_price("1.9")
        milestone = PaymentMilestone(title="Instalment 1", percentage=Decimal("50"), contract=contract)
        with pytest.raises(ValueError, match="190%"):
            invoicing.generate_deposit_invoice(contract, _project(contract), milestone, number="2026-001", date=DATE)

    def test_final(self):
        contract = _fixed_price("1.9")
        with pytest.raises(ValueError, match="190%"):
            invoicing.generate_final_invoice(contract, _project(contract), [], number="2026-001", date=DATE)

    def test_charges(self):
        contract = _contract("1.9")
        charge = ContractCharge(description="Travel", amount=Decimal("50"), basis=ChargeBasis.per_invoice)
        with pytest.raises(ValueError, match="190%"):
            invoicing.build_charge_items([charge], contract)

    def test_a_valid_rate_reaches_the_invoice_unchanged(self):
        contract = _fixed_price("0.19")
        invoice = invoicing.generate_fixed_price_invoice(contract, _project(contract), number="2026-001", date=DATE)
        assert [item.VAT_rate for item in invoice.items] == [Decimal("0.19")]


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _stored_project(engine, contract: Contract, milestones: int = 0) -> tuple[int, list[int]]:
    """Persist ``contract`` as is, bypassing the validation of the save paths."""
    with Session(engine) as session:
        session.add(
            User(
                name="Harry Tuttle",
                subtitle="Heating Engineer",
                email="mail@tuttle.example",
                VAT_number="27B-6",
                operating_country="Germany",
                address=Address(street="Main Street", number="450", postal_code="55555", city="Sao Paolo", country="Brazil"),
            )
        )
        contract.payment_milestones = [
            PaymentMilestone(title=f"Instalment {n + 1}", percentage=Decimal(100) / milestones, position=n)
            for n in range(milestones)
        ]
        project = _project(contract)
        session.add(project)
        session.commit()
        return project.id, [m.id for m in contract.payment_milestones]


def _invoice_count(engine) -> int:
    with Session(engine) as session:
        return len(session.exec(select(Invoice)).all())


REFUSAL = "The VAT rate of contract “Heating” is 190%. Correct it, then create the invoice."


class TestInvoicingIntent:
    """The user sees what is wrong and nothing is saved."""

    def test_time_based_invoice(self, in_memory_db):
        project_id, _ = _stored_project(in_memory_db, _contract("1.9"))
        result = InvoicingIntent().create(project_id, "2026-02-01", "2026-01-01", "2026-01-31")
        assert not result.was_intent_successful
        assert result.error_msg == REFUSAL
        assert _invoice_count(in_memory_db) == 0

    def test_invoice_with_typed_items(self, in_memory_db):
        project_id, _ = _stored_project(in_memory_db, _contract("1.9"))
        result = InvoicingIntent().create(
            project_id,
            "2026-02-01",
            "2026-01-01",
            "2026-01-31",
            manual_items=[{"description": "Repair", "quantity": 2, "unit": "hour", "unit_price": 100}],
        )
        assert result.error_msg == REFUSAL
        assert _invoice_count(in_memory_db) == 0

    def test_fixed_price_invoice(self, in_memory_db):
        project_id, _ = _stored_project(in_memory_db, _fixed_price("1.9"))
        result = InvoicingIntent().create(project_id, "2026-02-01", "2026-01-01", "2026-01-31")
        assert result.error_msg == REFUSAL
        assert _invoice_count(in_memory_db) == 0

    def test_deposit_invoice(self, in_memory_db):
        project_id, (first, _second) = _stored_project(in_memory_db, _fixed_price("1.9"), milestones=2)
        result = InvoicingIntent().create_deposit(project_id, first, DATE)
        assert result.error_msg == REFUSAL
        assert _invoice_count(in_memory_db) == 0

    def test_final_invoice(self, in_memory_db):
        project_id, _ = _stored_project(in_memory_db, _fixed_price("1.9"), milestones=1)
        result = InvoicingIntent().create_final(project_id, DATE)
        assert result.error_msg == REFUSAL
        assert _invoice_count(in_memory_db) == 0
