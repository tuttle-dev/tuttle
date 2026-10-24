"""An e-invoice states no country or tax currency that Tuttle guessed.

A country name that did not resolve to an ISO code became Germany, and so did
an empty one; a missing operating country was taken for Germany too, and a
country without a tax model accounted VAT in euros. Now an invoice whose
country does not resolve, or whose user has no operating country, is saved
without e-invoice data, with a warning that says what to correct.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.data_dir import get_data_dir
from tuttle.einvoice import country_to_iso, missing_details, serialize_zugferd_xml
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, PaymentMilestone, Project, User
from tuttle.tax import ALL_COUNTRIES
from tuttle.time import ContractType, Cycle

DATE = datetime.date(2026, 2, 1)


def _address(country: str) -> Address:
    return Address(street="Main Street", number="42", postal_code="55555", city="Somewhere", country=country)


def _user(country: str = "Germany", operating_country: str = "Germany") -> User:
    return User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        email="mail@tuttle.example",
        VAT_number="DE123456789",
        operating_country=operating_country,
        address=_address(country),
    )


def _contract(client_country: str = "Germany") -> Contract:
    return Contract(
        title="Duct Inspection",
        client=Client(name="Central Services", address=_address(client_country)),
        start_date=datetime.date(2026, 1, 10),
        rate=Decimal("80"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )


def _invoice(contract: Contract) -> Invoice:
    item = InvoiceItem(quantity=8, unit="hour", unit_price=Decimal("80"), VAT_rate=Decimal("0.19"), description="Inspection")
    return Invoice(number="2026-02-01-01", date=DATE, contract=contract, items=[item])


class TestCountryToISO:
    @pytest.mark.parametrize(
        "name, code",
        [("Schweiz", "CH"), ("Česko", "CZ"), ("Brasil", "BR"), ("Deutschland", "DE"), ("Österreich", "AT")],
    )
    def test_reads_names_in_other_languages(self, name, code):
        assert country_to_iso(name) == code

    @pytest.mark.parametrize("name", ["Schweitz", "Atlantis", "", "   "])
    def test_an_unknown_name_is_no_country(self, name):
        assert country_to_iso(name) is None

    @pytest.mark.parametrize("name", ["Korea", "Republic of Korea", "Victoria"])
    def test_guesses_no_close_match(self, name):
        # A fuzzy search took these for North Korea and Australia.
        assert country_to_iso(name) is None

    def test_a_two_letter_code_must_exist(self):
        assert country_to_iso("ZZ") is None
        assert country_to_iso("gb") == "GB"


class TestMissingDetails:
    def test_names_whose_country_is_not_recognised(self):
        message = missing_details(_invoice(_contract("Schweitz")), _user())

        assert message == "Correct the country of Central Services' address: 'Schweitz' is not recognised."

    def test_checks_the_seller_country_too(self):
        message = missing_details(_invoice(_contract()), _user(country="Atlantis"))

        assert message == "Correct the country of your address: 'Atlantis' is not recognised."

    def test_an_empty_country_is_not_taken_for_germany(self):
        assert missing_details(_invoice(_contract("")), _user()) == "Add the country of Central Services' address."

    def test_needs_the_operating_country(self):
        message = missing_details(_invoice(_contract()), _user(operating_country=""))

        assert message == "Add your operating country."

    def test_a_client_without_an_address_states_no_country(self):
        contract = _contract()
        contract.client.address = None

        assert missing_details(_invoice(contract), _user()) is None

    def test_recognised_countries_need_nothing(self):
        assert missing_details(_invoice(_contract("Schweiz")), _user()) is None


class TestTheEInvoice:
    def test_writes_the_country_read_from_a_local_name(self):
        xml = serialize_zugferd_xml(_invoice(_contract("Schweiz")), _user()).decode()
        buyer = xml.split("<ram:BuyerTradeParty>")[1].split("</ram:BuyerTradeParty>")[0]

        assert "<ram:CountryID>CH</ram:CountryID>" in buyer

    def test_refuses_an_unrecognised_country_instead_of_writing_germany(self):
        with pytest.raises(ValueError, match="'Schweitz' is not recognised"):
            serialize_zugferd_xml(_invoice(_contract("Schweitz")), _user())

    def test_takes_no_operating_country_for_germany(self):
        with pytest.raises(ValueError, match="operating country is not set"):
            serialize_zugferd_xml(_invoice(_contract()), _user(operating_country=""))

    def test_a_country_without_a_tax_model_accounts_vat_in_its_own_currency(self):
        xml = serialize_zugferd_xml(_invoice(_contract()), _user(operating_country="Switzerland")).decode()

        assert "<ram:TaxCurrencyCode>CHF</ram:TaxCurrencyCode>" in xml
        assert '<ram:TaxTotalAmount currencyID="CHF">' in xml


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _project(engine, contract: Contract) -> tuple[int, list[int]]:
    """Persist a project on *contract*: its id and its milestones' ids."""
    with Session(engine) as session:
        session.add(_user())
        project = Project(
            title="Duct Inspection",
            description="Ducts",
            tag="#ducts",
            start_date=datetime.date(2026, 1, 10),
            contract=contract,
        )
        session.add(project)
        session.commit()
        return project.id, [m.id for m in contract.payment_milestones]


class TestIssuing:
    """Tuttle does not refuse the invoice: it leaves out the e-invoice data and says what to correct."""

    WARNING = "Saved without e-invoice data. Correct the country of Central Services' address: 'Schweitz' is not recognised."

    def test_an_invoice_is_saved_with_its_pdf_and_a_warning(self, db):
        project_id, _ = _project(db, _contract("Schweitz"))

        result = InvoicingIntent().create(project_id, DATE, DATE, DATE, manual_quantity=8)

        assert result.was_intent_successful, result.error_msg
        assert result.warning == self.WARNING
        assert (get_data_dir() / "Invoices" / result.data.file_name).exists()
        with Session(db) as session:
            assert len(session.exec(select(Invoice)).all()) == 1

    def test_a_deposit_invoice_too(self, db):
        contract = _contract("Schweitz")
        contract.type = ContractType.fixed_price
        contract.fixed_price = Decimal("10000")
        contract.payment_milestones = [PaymentMilestone(title="On signing", percentage=Decimal("40"), position=0)]
        project_id, (milestone_id,) = _project(db, contract)

        result = InvoicingIntent().create_deposit(project_id, milestone_id, DATE)

        assert result.was_intent_successful, result.error_msg
        assert result.warning == self.WARNING

    def test_no_warning_when_the_countries_are_recognised(self, db):
        project_id, _ = _project(db, _contract("Schweiz"))

        result = InvoicingIntent().create(project_id, DATE, DATE, DATE, manual_quantity=8)

        assert result.was_intent_successful, result.error_msg
        assert not result.warning


@pytest.mark.parametrize(
    "name, code",
    [("Turkey", "TR"), ("UK", "GB"), ("Great Britain", "GB"), ("England", "GB"), ("Scotland", "GB")],
)
def test_everyday_english_names_resolve(name, code):
    assert country_to_iso(name) == code


def test_every_operating_country_on_offer_resolves():
    assert [c for c in ALL_COUNTRIES if country_to_iso(c) is None] == []
