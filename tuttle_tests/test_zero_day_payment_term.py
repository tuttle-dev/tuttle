"""A payment term of 0 days makes an invoice due on its date.

Only a contract without a term leaves its invoices without a due date.
"""

import datetime
from decimal import Decimal

import pytest
from lxml import etree
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle import rendering
from tuttle.app.contracts.intent import ContractsIntent
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.preferences.model import INVOICE_TEMPLATES
from tuttle.einvoice import serialize_zugferd_xml
from tuttle.kpi import compute_kpis
from tuttle.model import Address, BankAccount, Client, Contract, Invoice, InvoiceItem, User
from tuttle.time import Cycle, TimeUnit

TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)

NS = {
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}


def _user() -> User:
    return User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        email="mail@tuttle.example",
        VAT_number="DE123456789",
        operating_country="Germany",
        address=Address(street="Main Street", number="450", postal_code="10115", city="Berlin", country="Germany"),
        bank_accounts=[BankAccount(name="Harry Tuttle", IBAN="DE89370400440532013000", BIC="COBADEFFXXX")],
    )


def _invoice(term_of_payment, date: datetime.date = TODAY, sent: bool = True) -> Invoice:
    contract = Contract(
        title="Boiler Maintenance",
        client=Client(
            name="Sam Lowry",
            address=Address(street="Shangrila Towers", number="1", postal_code="10115", city="Berlin", country="Germany"),
        ),
        start_date=datetime.date(2026, 1, 1),
        rate=Decimal("80.00"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=term_of_payment,
        billing_cycle=Cycle.monthly,
    )
    invoice = Invoice(number="2026-001", date=date, contract=contract, sent=sent)
    InvoiceItem(
        invoice=invoice,
        start_date=date,
        end_date=date,
        quantity=10,
        unit="hour",
        unit_price=Decimal("80.00"),
        VAT_rate=Decimal("0.19"),
        description="Boiler service",
    )
    return invoice


class TestDueDate:
    def test_a_0_day_term_is_due_on_the_invoice_date(self):
        invoice = _invoice(0, date=datetime.date(2026, 4, 1))
        assert invoice.due_date == invoice.effective_due_date == datetime.date(2026, 4, 1)

    def test_no_term_means_no_due_date(self):
        assert _invoice(None).due_date is None

    def test_it_is_overdue_from_the_next_day(self):
        assert _invoice(0, date=TODAY).status == "sent"
        assert _invoice(0, date=YESTERDAY).status == "overdue"

    def test_it_counts_as_overdue_on_the_dashboard(self):
        invoice = _invoice(0, date=YESTERDAY)
        kpis = compute_kpis([invoice], [], [], country="Germany")
        assert kpis.overdue_invoices == 1
        assert kpis.overdue_amount == invoice.total


class TestDocuments:
    @pytest.mark.parametrize("template_name", list(INVOICE_TEMPLATES))
    def test_the_pdf_shows_the_due_date(self, template_name):
        def render(term_of_payment):
            invoice = _invoice(term_of_payment, date=datetime.date(2026, 4, 1))
            return rendering.render_invoice(
                user=_user(), invoice=invoice, out_dir=None, document_format="html", template_name=template_name
            )

        assert "Due Date" in render(0)
        assert "Due Date" not in render(None)

    def test_the_e_invoice_states_the_due_date_and_terms(self):
        """EN16931 BR-CO-25: an amount due needs a due date (BT-9) or payment terms (BT-20)."""
        invoice = _invoice(0, date=datetime.date(2026, 4, 1))
        xml = etree.fromstring(serialize_zugferd_xml(invoice, _user(), profile="EN16931"))
        terms = xml.find(".//ram:SpecifiedTradePaymentTerms", NS)
        assert terms.findtext("ram:DueDateDateTime/udt:DateTimeString", namespaces=NS) == "20260401"
        assert terms.findtext("ram:Description", namespaces=NS) == "Net 0 days"

    def test_the_e_invoice_of_a_contract_without_term_has_no_terms(self):
        xml = serialize_zugferd_xml(_invoice(None), _user(), profile="EN16931").decode("utf-8")
        assert "SpecifiedTradePaymentTerms" not in xml


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def test_a_contract_keeps_its_0_day_term(in_memory_db):
    result = ContractsIntent().save_from_dict(
        {
            "title": "Boiler Maintenance",
            "type": "time_based",
            "rate": 80,
            "currency": "EUR",
            "unit": "hour",
            "billing_cycle": "monthly",
            "units_per_workday": 8,
            "expected_units_per_week": 10,
            "VAT_rate": 0.19,
            "start_date": "2026-01-01",
            "term_of_payment": 0,
        }
    )
    assert result.was_intent_successful, result.error_msg
    with Session(in_memory_db) as session:
        assert session.exec(select(Contract)).one().term_of_payment == 0
