"""An e-invoice states no country or tax currency that Tuttle guessed.

A country name that did not resolve to an ISO code became Germany, and so did
an empty one; a missing operating country was taken for Germany too, and a
country without a tax model accounted VAT in euros. Now a country that does
not resolve refuses issuing with a message that says whose it is, and the tax
currency comes from the operating country or nowhere.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.einvoice import country_to_iso, serialize_zugferd_xml
from tuttle.invoicing import missing_mandatory_details
from tuttle.model import Address, Client, Contract, Invoice, InvoiceItem, Project, User
from tuttle.tax import ALL_COUNTRIES
from tuttle.time import Cycle

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


class TestIssuingChecksTheCountries:
    def test_names_whose_country_is_not_recognised(self):
        message = missing_mandatory_details(_user(), _contract("Schweitz"), "EN16931")

        assert message == "Correct the country of Central Services' address: 'Schweitz' is not recognised."

    def test_checks_the_seller_country_too(self):
        message = missing_mandatory_details(_user(country="Atlantis"), _contract(), "EN16931")

        assert message == "Correct the country of your address: 'Atlantis' is not recognised."

    def test_follows_what_is_missing(self):
        user = _user(country="Atlantis")
        user.VAT_number = None

        message = missing_mandatory_details(user, _contract(), "EN16931")

        assert message == (
            "Add your VAT number or tax number before issuing this invoice. "
            "Correct the country of your address: 'Atlantis' is not recognised."
        )

    def test_a_pdf_alone_prints_the_country_as_written(self):
        assert missing_mandatory_details(_user(), _contract("Schweitz"), None) is None

    def test_an_e_invoice_needs_the_operating_country(self):
        user = _user(operating_country="")

        assert missing_mandatory_details(user, _contract(), "EN16931") == (
            "Add your operating country before issuing this invoice."
        )
        assert missing_mandatory_details(user, _contract(), None) is None


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


def test_issuing_is_refused_before_anything_is_saved(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    with Session(engine) as session:
        session.add(_user())
        project = Project(
            title="Duct Inspection",
            description="Ducts",
            tag="#ducts",
            start_date=datetime.date(2026, 1, 10),
            contract=_contract("Schweitz"),
        )
        session.add(project)
        session.commit()
        project_id = project.id

    result = InvoicingIntent().create(project_id, DATE, DATE, DATE, manual_quantity=8)

    assert result.error_msg == "Correct the country of Central Services' address: 'Schweitz' is not recognised."
    with Session(engine) as session:
        assert session.exec(select(Invoice)).all() == []


@pytest.mark.parametrize(
    "name, code",
    [("Turkey", "TR"), ("UK", "GB"), ("Great Britain", "GB"), ("England", "GB"), ("Scotland", "GB")],
)
def test_everyday_english_names_resolve(name, code):
    assert country_to_iso(name) == code


def test_every_operating_country_on_offer_resolves():
    assert [c for c in ALL_COUNTRIES if country_to_iso(c) is None] == []
