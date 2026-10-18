"""No invoice is issued without the details the law requires.

§14 Abs. 4 UStG and EN16931 want the seller's name, address and VAT number or
tax number, and the buyer's name and address; an e-invoice also wants payment
terms. The documents left out whatever was missing and the XML still passed
schema validation, so nobody noticed. Issuing is now refused with a message
that names what to add, before a number is taken or anything is saved.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle import demo
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.einvoice import serialize_zugferd_xml
from tuttle.invoicing import missing_mandatory_details
from tuttle.model import (
    Address,
    Client,
    Contact,
    Contract,
    Invoice,
    InvoiceItem,
    PaymentMilestone,
    Project,
    TaxCategory,
    User,
)
from tuttle.time import ContractType, Cycle

DATE = datetime.date(2026, 2, 1)


def _address(**overrides) -> Address:
    fields = dict(street="Main Street", number="42", postal_code="55555", city="Somewhere", country="Germany")
    return Address(**{**fields, **overrides})


def _user(**overrides) -> User:
    fields = dict(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        email="mail@tuttle.example",
        VAT_number="DE123456789",
        address=_address(number="450"),
    )
    return User(**{**fields, **overrides})


def _contract(client: Client, **overrides) -> Contract:
    fields = dict(
        title="Duct Inspection",
        client=client,
        start_date=datetime.date(2026, 1, 10),
        rate=Decimal("80"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Contract(**{**fields, **overrides})


def _central_services(**overrides) -> Client:
    return Client(**{"name": "Central Services", "address": _address(), **overrides})


class TestMissingMandatoryDetails:
    def test_complete_details_pass(self):
        assert missing_mandatory_details(_user(), _contract(_central_services()), "EN16931") is None

    def test_names_everything_that_is_missing_in_one_message(self):
        user = _user(VAT_number=None)
        contract = _contract(_central_services(address=None))

        assert missing_mandatory_details(user, contract) == (
            "Add your VAT number or tax number and Central Services' address before issuing this invoice."
        )

    def test_names_the_parts_of_an_incomplete_address(self):
        user = _user(address=_address(street="", city=" "))

        assert missing_mandatory_details(user, _contract(_central_services())) == (
            "Add the street and city of your address before issuing this invoice."
        )

    def test_house_number_and_postcode_are_not_required(self):
        user = _user(address=_address(number="", postal_code=""))

        assert missing_mandatory_details(user, _contract(_central_services())) is None

    def test_a_tax_number_identifies_the_seller_too(self):
        user = _user(VAT_number=None, tax_number="21/815/08150")

        assert missing_mandatory_details(user, _contract(_central_services())) is None

    def test_outside_the_scope_of_vat_the_tax_number_is_needed(self):
        # BR-O-02 keeps the VAT number off such an invoice.
        contract = _contract(_central_services(), VAT_rate=Decimal("0"), VAT_category=TaxCategory.outside_scope)

        assert missing_mandatory_details(_user(), contract) == "Add your tax number before issuing this invoice."
        assert missing_mandatory_details(_user(tax_number="21/815/08150"), contract) is None

    def test_names_the_invoicing_contact_whose_address_is_printed(self):
        contact = Contact(first_name="Jill", last_name="Layton", address=_address(city=""))
        client = _central_services(invoicing_contact=contact)

        assert missing_mandatory_details(_user(), _contract(client)) == (
            "Add the city of Jill Layton's address before issuing this invoice."
        )

    def test_the_client_address_serves_when_the_contact_has_none(self):
        client = _central_services(invoicing_contact=Contact(first_name="Jill", last_name="Layton"))

        assert missing_mandatory_details(_user(), _contract(client)) is None

    def test_an_e_invoice_needs_a_term_of_payment(self):
        contract = _contract(_central_services(), term_of_payment=None)

        assert missing_mandatory_details(_user(), contract, "EN16931") == (
            "Add the contract's term of payment before issuing this invoice."
        )
        assert missing_mandatory_details(_user(), contract, None) is None

    def test_a_term_of_zero_days_is_a_term(self):
        contract = _contract(_central_services(), term_of_payment=0)

        assert missing_mandatory_details(_user(), contract, "EN16931") is None

    def test_names_the_document(self):
        user = _user(VAT_number=None)

        message = missing_mandatory_details(user, _contract(_central_services()), document="reminder")

        assert message == "Add your VAT number or tax number before issuing this reminder."


def test_the_e_invoice_states_the_address_the_pdf_shows():
    """A client reached through its invoicing contact has the contact's address on both documents."""
    contact = Contact(first_name="Jill", last_name="Layton", address=_address(street="Ministry Road", city="Somewhere"))
    contract = _contract(Client(name="Central Services", invoicing_contact=contact))
    invoice = Invoice(
        number="2026-02-01-01",
        date=DATE,
        contract=contract,
        items=[
            InvoiceItem(
                quantity=8, unit="hour", unit_price=Decimal("80"), VAT_rate=Decimal("0.19"), description="Duct inspection"
            )
        ],
    )

    xml = serialize_zugferd_xml(invoice, _user(operating_country="Germany")).decode()
    buyer = xml.split("<ram:BuyerTradeParty>")[1].split("</ram:BuyerTradeParty>")[0]

    assert "<ram:LineOne>Ministry Road 42</ram:LineOne>" in buyer
    assert "<ram:CityName>Somewhere</ram:CityName>" in buyer


def test_the_demo_satisfies_the_check():
    user = demo.create_demo_user()
    projects, _invoices, _contacts = demo.create_heating_data(user)

    refusals = {p.contract.title: missing_mandatory_details(user, p.contract, "EN16931") for p in projects}

    assert {title: message for title, message in refusals.items() if message} == {}


# -- Issuing ------------------------------------------------------------------


@pytest.fixture
def engine(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _persist(engine, user: User, contract: Contract) -> int:
    with Session(engine) as session:
        session.add(user)
        project = Project(
            title="Duct Inspection",
            description="Ducts",
            tag="#ducts",
            start_date=datetime.date(2026, 1, 10),
            contract=contract,
        )
        session.add(project)
        session.commit()
        return project.id


def _invoices(engine) -> list[Invoice]:
    with Session(engine) as session:
        return list(session.exec(select(Invoice)).all())


def _fixed_price(**overrides) -> Contract:
    return _contract(
        _central_services(address=None),
        type=ContractType.fixed_price,
        rate=None,
        fixed_price=Decimal("10000"),
        payment_milestones=[
            PaymentMilestone(title="Upfront", percentage=Decimal("40"), position=0),
            PaymentMilestone(title="On delivery", percentage=Decimal("60"), position=1),
        ],
        **overrides,
    )


EXPECTED = "Add your VAT number or tax number and Central Services' address before issuing this {}."


class TestIssuingIsRefused:
    def test_for_an_invoice(self, engine):
        project_id = _persist(engine, _user(VAT_number=None), _contract(_central_services(address=None)))

        result = InvoicingIntent().create(
            project_id,
            DATE,
            DATE,
            DATE,
            manual_items=[{"description": "Inspection", "quantity": 8, "unit": "hour", "unit_price": 80}],
        )

        assert not result.was_intent_successful
        assert result.error_msg == EXPECTED.format("invoice")
        assert _invoices(engine) == []

    def test_for_a_deposit_invoice(self, engine):
        project_id = _persist(engine, _user(VAT_number=None), _fixed_price())
        intent = InvoicingIntent()
        milestone_id = intent._projects_intent.get_by_id(project_id).data.contract.payment_milestones[0].id

        result = intent.create_deposit(project_id, milestone_id, DATE)

        assert result.error_msg == EXPECTED.format("deposit invoice")
        assert _invoices(engine) == []
        with Session(engine) as session:
            assert not session.get(PaymentMilestone, milestone_id).invoiced

    def test_for_a_final_invoice(self, engine):
        project_id = _persist(engine, _user(VAT_number=None), _fixed_price())

        result = InvoicingIntent().create_final(project_id, DATE)

        assert result.error_msg == EXPECTED.format("final invoice")
        assert _invoices(engine) == []

    def test_for_a_reminder(self, engine):
        project_id = _persist(engine, _user(), _contract(_central_services()))
        intent = InvoicingIntent()
        invoice = intent.create(project_id, DATE, DATE, DATE, manual_quantity=8).data
        with Session(engine) as session:
            session.exec(select(User)).one().VAT_number = None
            session.commit()

        result = intent.create_reminder(invoice.id, "2026-03-01", "2026-03-15")

        assert result.error_msg == "Add your VAT number or tax number before issuing this reminder."
        assert [inv.id for inv in _invoices(engine)] == [invoice.id]

    def test_for_an_e_invoice_without_a_term_of_payment(self, engine):
        project_id = _persist(engine, _user(), _contract(_central_services()))
        with Session(engine) as session:
            # Cleared on an existing contract; a new one would get the default term.
            session.exec(select(Contract)).one().term_of_payment = None
            session.commit()

        result = InvoicingIntent().create(project_id, DATE, DATE, DATE, manual_quantity=8)

        assert result.error_msg == "Add the contract's term of payment before issuing this invoice."
        assert _invoices(engine) == []


def test_complete_details_issue_the_invoice(engine):
    project_id = _persist(engine, _user(), _contract(_central_services()))

    result = InvoicingIntent().create(project_id, DATE, DATE, DATE, manual_quantity=8)

    assert result.was_intent_successful, result.error_msg
    assert len(_invoices(engine)) == 1
