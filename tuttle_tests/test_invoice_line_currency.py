"""Invoice lines show the currency of the contract, in the app and on the PDF."""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine

from tuttle import rendering
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.core.rpc_utils import dump
from tuttle.app.invoicing.data_source import InvoicingDataSource
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.app.preferences.model import INVOICE_TEMPLATES
from tuttle.model import (
    Address,
    Client,
    Contract,
    Invoice,
    InvoiceItem,
    PaymentMilestone,
    Project,
    TaxCategory,
    User,
)
from tuttle.time import ContractType, Cycle, TimeUnit


def _user() -> User:
    return User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        email="mail@tuttle.example",
        tax_number="12/345/67890",
        operating_country="Germany",
        address=Address(street="Main Street", number="450", postal_code="10115", city="Berlin", country="Germany"),
    )


def _usd_contract(**pricing) -> Contract:
    """A contract with a US client, outside the scope of German VAT."""
    return Contract(
        title="Boiler Consulting",
        client=Client(
            name="Sam Lowry",
            address=Address(street="Fifth Avenue", number="1", postal_code="10001", city="New York", country="United States"),
        ),
        start_date=datetime.date(2026, 1, 1),
        currency="USD",
        VAT_rate=Decimal("0"),
        VAT_category=TaxCategory.outside_scope,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
        **(pricing or dict(rate=Decimal("120.00"), unit=TimeUnit.hour, units_per_workday=8)),
    )


def _item(invoice=None) -> InvoiceItem:
    return InvoiceItem(
        invoice=invoice,
        start_date=datetime.date(2026, 3, 1),
        end_date=datetime.date(2026, 3, 31),
        quantity=2,
        unit="hour",
        unit_price=Decimal("120.00"),
        VAT_rate=Decimal("0"),
        VAT_category=TaxCategory.outside_scope,
        description="Boiler consulting",
    )


def _usd_invoice() -> Invoice:
    invoice = Invoice(number="2026-001", date=datetime.date(2026, 4, 1), contract=_usd_contract())
    _item(invoice)
    return invoice


class TestLineAmounts:
    def test_are_in_the_invoice_currency(self):
        (item,) = _usd_invoice().items
        assert (item.unit_price_formatted, item.subtotal_formatted) == ("$120.00", "$240.00")

    def test_a_line_on_no_invoice_falls_back_to_euro(self):
        item = _item()
        assert (item.unit_price_formatted, item.subtotal_formatted) == ("€120.00", "€240.00")


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _persist(engine, contract: Contract) -> tuple[int, list[int]]:
    """Store a project under ``contract``; return its id and its milestones' ids."""
    with Session(engine) as session:
        session.add(_user())
        project = Project(
            title="Boiler Consulting",
            description="Advice on the ductwork",
            tag="#consulting",
            contract=contract,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        session.add(project)
        session.commit()
        return project.id, [milestone.id for milestone in contract.payment_milestones]


def _rpc_items(invoice: dict) -> list[tuple[str, str]]:
    return [(item["unit_price_formatted"], item["subtotal_formatted"]) for item in invoice["items"]]


class TestInvoicesReadBackFromTheDatabase:
    """The app lists invoices loaded in a session that has closed by the time
    the lines are formatted."""

    def test_lines_are_in_the_invoice_currency(self, in_memory_db):
        project_id, _ = _persist(in_memory_db, _usd_contract())
        result = InvoicingIntent().create(
            project_id,
            "2026-04-01",
            "2026-03-01",
            "2026-03-31",
            manual_items=[{"description": "Boiler consulting", "quantity": 2, "unit": "hour", "unit_price": "120.00"}],
        )
        assert result.was_intent_successful, result.error_msg

        (invoice,) = [dump(invoice) for invoice in InvoicingDataSource().get_all_invoices().data]
        assert _rpc_items(invoice) == [("$120.00", "$240.00")]

    def test_deposit_lines_inside_a_final_invoice_are_in_its_currency(self, in_memory_db):
        contract = _usd_contract(type=ContractType.fixed_price, fixed_price=Decimal("10000"))
        contract.payment_milestones = [
            PaymentMilestone(title=f"Instalment {position + 1}", percentage=Decimal("50"), position=position)
            for position in range(2)
        ]
        project_id, milestone_ids = _persist(in_memory_db, contract)
        intent = InvoicingIntent()
        for milestone_id in milestone_ids:  # the last milestone settles the contract with a final invoice
            result = intent.create_deposit(project_id, milestone_id, datetime.date(2026, 2, 1))
            assert result.was_intent_successful, result.error_msg

        invoices = [dump(invoice) for invoice in InvoicingDataSource().get_all_invoices().data]
        (final,) = [invoice for invoice in invoices if invoice["document_type"] == "final"]
        assert _rpc_items(final) == [("$10,000.00", "$10,000.00")]
        assert [_rpc_items(deposit) for deposit in final["deposits"]] == [[("$5,000.00", "$5,000.00")]]


@pytest.mark.parametrize("template_name", list(INVOICE_TEMPLATES))
def test_no_template_prints_euro_on_a_dollar_invoice(template_name):
    html = rendering.render_invoice(
        user=_user(), invoice=_usd_invoice(), out_dir=None, document_format="html", template_name=template_name
    )
    assert "$240.00" in html
    assert "€" not in html
