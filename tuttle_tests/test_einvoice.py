"""Tests for the ZUGFeRD / Factur-X e-invoice generation."""

import datetime
import re
from decimal import Decimal

import pytest
from lxml import etree

from tuttle.einvoice import (
    build_zugferd_document,
    country_to_iso,
    serialize_zugferd_xml,
    unit_to_unece,
)
from tuttle.model import (
    Address,
    BankAccount,
    Client,
    Contract,
    Invoice,
    InvoiceItem,
    Project,
    TaxCategory,
    User,
)
from tuttle.time import Cycle, TimeUnit

# -- Helper fixtures ----------------------------------------------------------


def _make_user() -> User:
    return User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        email="mail@tuttle.example",
        VAT_number="DE123456789",
        address=Address(
            street="Hauptstraße",
            number="42",
            postal_code="10115",
            city="Berlin",
            country="Germany",
        ),
        bank_account=BankAccount(
            name="Business",
            IBAN="DE89370400440532013000",
            BIC="COBADEFFXXX",
        ),
    )


def _make_invoice() -> Invoice:
    client = Client(
        name="Central Services GmbH",
        vat_number="DE987654321",
        address=Address(
            street="Industriestraße",
            number="7",
            postal_code="80331",
            city="München",
            country="Germany",
        ),
    )
    contract = Contract(
        title="Heating Maintenance",
        client=client,
        start_date=datetime.date(2024, 1, 1),
        rate=Decimal("100.00"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=30,
        billing_cycle=Cycle.monthly,
    )
    project = Project(
        title="Q1 Maintenance",
        tag="#Maintenance",
        contract=contract,
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2024, 3, 31),
    )
    items = [
        InvoiceItem(
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 1, 31),
            quantity=40.0,
            unit="hour",
            unit_price=Decimal("100.00"),
            description="Heating system maintenance - January",
            VAT_rate=Decimal("0.19"),
        ),
        InvoiceItem(
            start_date=datetime.date(2024, 2, 1),
            end_date=datetime.date(2024, 2, 29),
            quantity=32.0,
            unit="hour",
            unit_price=Decimal("100.00"),
            description="Heating system maintenance - February",
            VAT_rate=Decimal("0.19"),
        ),
    ]
    return Invoice(
        number="2024-03-15-01",
        date=datetime.date(2024, 3, 15),
        contract=contract,
        project=project,
        items=items,
    )


# -- Unit tests: helpers ------------------------------------------------------


class TestCountryToISO:
    def test_full_name(self):
        assert country_to_iso("Germany") == "DE"

    def test_already_code(self):
        assert country_to_iso("DE") == "DE"
        assert country_to_iso("fr") == "FR"

    def test_fuzzy(self):
        assert country_to_iso("United States") == "US"

    def test_empty_default(self):
        assert country_to_iso("") == "DE"


class TestUnitToUNECE:
    def test_known_units(self):
        assert unit_to_unece("hour") == "HUR"
        assert unit_to_unece("hours") == "HUR"
        assert unit_to_unece("day") == "DAY"
        assert unit_to_unece("days") == "DAY"
        assert unit_to_unece("month") == "MON"
        assert unit_to_unece("unit") == "C62"

    def test_unknown_fallback(self):
        assert unit_to_unece("widgets") == "C62"


# -- Integration test: XML generation ----------------------------------------


class TestBuildZugferdDocument:
    def test_builds_valid_document(self):
        user = _make_user()
        invoice = _make_invoice()
        doc = build_zugferd_document(invoice, user, profile="EN16931")
        assert doc is not None
        assert str(doc.header.id) == "2024-03-15-01"
        assert str(doc.header.type_code) == "380"

    def test_serialize_produces_valid_xml(self):
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(invoice, user, profile="EN16931")

        assert xml_bytes is not None
        assert len(xml_bytes) > 0

        root = etree.fromstring(xml_bytes)
        assert root.tag is not None
        assert "CrossIndustryInvoice" in root.tag

    def test_xml_contains_seller_info(self):
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(invoice, user, profile="EN16931")
        xml_str = xml_bytes.decode("utf-8")

        assert "Harry Tuttle" in xml_str
        assert "DE123456789" in xml_str
        assert "DE89370400440532013000" in xml_str

    @staticmethod
    def _seller_party(xml_str: str) -> str:
        return re.search(
            r"<ram:SellerTradeParty>.*?</ram:SellerTradeParty>", xml_str, re.S
        ).group(0)

    def test_seller_tax_number_falls_back_to_scheme_fc_without_vat_number(self):
        """A freelancer awaiting the USt-IdNr still owes a §14 UStG identifier;
        on a standard (in-scope) invoice CII carries it under scheme FC."""
        user = _make_user()
        user.VAT_number = None
        user.tax_number = "21/815/08150"
        invoice = _make_invoice()
        xml_str = serialize_zugferd_xml(
            invoice, user, profile="EN16931", validate=True
        ).decode("utf-8")
        seller = self._seller_party(xml_str)
        assert '<ram:ID schemeID="FC">21/815/08150</ram:ID>' in seller
        assert 'schemeID="VA"' not in seller

    def test_seller_vat_number_wins_over_tax_number_when_both_set(self):
        user = _make_user()
        user.tax_number = "21/815/08150"
        invoice = _make_invoice()
        xml_str = serialize_zugferd_xml(invoice, user, profile="EN16931").decode(
            "utf-8"
        )
        assert '<ram:ID schemeID="VA">DE123456789</ram:ID>' in xml_str
        assert "21/815/08150" not in xml_str

    def test_no_seller_tax_identifier_without_vat_or_tax_number(self):
        user = _make_user()
        user.VAT_number = None
        user.tax_number = None
        invoice = _make_invoice()
        xml_str = serialize_zugferd_xml(invoice, user, profile="EN16931").decode(
            "utf-8"
        )
        seller = self._seller_party(xml_str)
        assert 'schemeID="VA"' not in seller
        assert 'schemeID="FC"' not in seller

    def test_xml_contains_buyer_info(self):
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(invoice, user, profile="EN16931")
        xml_str = xml_bytes.decode("utf-8")

        assert "Central Services GmbH" in xml_str
        assert "DE987654321" in xml_str

    def test_xml_contains_line_items(self):
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(invoice, user, profile="EN16931")
        xml_str = xml_bytes.decode("utf-8")

        assert "Heating system maintenance - January" in xml_str
        assert "Heating system maintenance - February" in xml_str

    def test_monetary_totals_correct(self):
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(invoice, user, profile="EN16931")
        xml_str = xml_bytes.decode("utf-8")

        # 40h + 32h = 72h @ 100 EUR = 7200 net; 19% VAT = 1368; total = 8568
        assert "7200" in xml_str
        assert "1368" in xml_str
        assert "8568" in xml_str

    def test_schema_validation_passes(self):
        """serialize with schema validation enabled should not raise."""
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(
            invoice, user, profile="EN16931", validate=True
        )
        assert len(xml_bytes) > 0

    def test_zero_vat_schema_validation_passes(self):
        """0% VAT must not produce xs:decimal-invalid scientific notation (e.g. 0E-10)."""
        user = _make_user()
        invoice = _make_invoice()
        for item in invoice.items:
            item.VAT_rate = Decimal("0E-10")  # simulate what the DB can return
        xml_bytes = serialize_zugferd_xml(
            invoice, user, profile="EN16931", validate=True
        )
        assert len(xml_bytes) > 0
        assert b"0E-10" not in xml_bytes

    @pytest.mark.parametrize(
        "profile",
        ["EN16931", "EXTENDED", "BASIC", "MINIMUM"],
    )
    def test_schema_validation_all_profiles(self, profile):
        """All profiles with bundled schemas must produce valid XML."""
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(invoice, user, profile=profile, validate=True)
        assert len(xml_bytes) > 0

    def test_xrechnung_profile_serializes(self):
        """XRECHNUNG has no bundled schema; verify it serializes without error."""
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(
            invoice, user, profile="XRECHNUNG", validate=False
        )
        assert len(xml_bytes) > 0
        assert b"XRechnung" in xml_bytes

    def test_basic_profile_excludes_bic(self):
        """BASIC profile must not include BIC (issue #283 follow-up)."""
        user = _make_user()
        assert user.bank_account.BIC
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(invoice, user, profile="BASIC", validate=True)
        assert b"COBADEFFXXX" not in xml_bytes

    def test_minimum_profile_excludes_line_items(self):
        """MINIMUM profile must not include line items or payment means."""
        user = _make_user()
        invoice = _make_invoice()
        xml_bytes = serialize_zugferd_xml(
            invoice, user, profile="MINIMUM", validate=True
        )
        xml_str = xml_bytes.decode("utf-8")
        assert "IncludedSupplyChainTradeLineItem" not in xml_str
        assert "PayeePartyCreditorFinancialAccount" not in xml_str

    def test_embed_in_pdf(self, tmp_path):
        """Full round-trip: generate a PDF, embed ZUGFeRD XML, verify output."""
        from pypdf import PdfWriter

        from tuttle.einvoice import embed_zugferd_in_pdf

        user = _make_user()
        invoice = _make_invoice()

        # Create a minimal valid PDF
        pdf_path = tmp_path / "test-invoice.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        with open(pdf_path, "wb") as f:
            writer.write(f)

        original_size = pdf_path.stat().st_size
        embed_zugferd_in_pdf(
            pdf_path=str(pdf_path),
            invoice=invoice,
            user=user,
            profile="EN16931",
        )
        augmented_size = pdf_path.stat().st_size
        assert augmented_size > original_size


# -- Tax category "O" (outside the scope of tax) ------------------------------


def _make_outside_scope_invoice() -> Invoice:
    """The same invoice, re-cast as a supply outside the scope of German VAT."""
    invoice = _make_invoice()
    invoice.contract.VAT_rate = Decimal("0")
    invoice.contract.VAT_category = TaxCategory.outside_scope
    for item in invoice.items:
        item.VAT_rate = Decimal("0")
        item.VAT_category = TaxCategory.outside_scope
    return invoice


class TestOutsideScopeOfTax:
    """EN16931 category O, per the official CII schematron (BR-O-01 … BR-O-14)."""

    @staticmethod
    def _xml(user=None, invoice=None, profile="EN16931") -> str:
        user = user if user is not None else _make_user()
        invoice = invoice if invoice is not None else _make_outside_scope_invoice()
        return serialize_zugferd_xml(
            invoice, user, profile=profile, validate=True
        ).decode("utf-8")

    @staticmethod
    def _breakdowns(xml_str: str) -> list[str]:
        """The header-level VAT breakdown groups (BG-23), not the line-level ones."""
        settlement = re.search(
            r"<ram:ApplicableHeaderTradeSettlement>.*?"
            r"</ram:ApplicableHeaderTradeSettlement>",
            xml_str,
            re.S,
        ).group(0)
        return re.findall(
            r"<ram:ApplicableTradeTax>.*?</ram:ApplicableTradeTax>", settlement, re.S
        )

    def test_invoice_reports_outside_scope(self):
        assert _make_outside_scope_invoice().is_outside_scope is True
        assert _make_invoice().is_outside_scope is False

    def test_br_o_01_exactly_one_breakdown_with_category_o(self):
        breakdowns = self._breakdowns(self._xml())
        assert len(breakdowns) == 1
        assert "<ram:CategoryCode>O</ram:CategoryCode>" in breakdowns[0]

    def test_br_o_02_no_seller_or_buyer_vat_identifier(self):
        """An O invoice must not carry BT-31, BT-63 or BT-48."""
        user = _make_user()
        user.tax_number = "21/815/08150"
        assert user.VAT_number  # the seller has one; it must still be omitted
        xml_str = self._xml(user=user)
        assert 'schemeID="VA"' not in xml_str
        assert user.VAT_number not in xml_str

    def test_seller_tax_number_emitted_as_scheme_fc(self):
        """§14 UStG still wants an identifier; CII carries it under scheme FC."""
        user = _make_user()
        user.tax_number = "21/815/08150"
        xml_str = self._xml(user=user)
        assert '<ram:ID schemeID="FC">21/815/08150</ram:ID>' in xml_str

    def test_no_tax_identifier_when_user_has_no_tax_number(self):
        user = _make_user()
        user.tax_number = None
        xml_str = self._xml(user=user)
        assert 'schemeID="FC"' not in xml_str
        assert 'schemeID="VA"' not in xml_str

    def test_br_o_05_line_items_carry_no_vat_rate(self):
        xml_str = self._xml()
        assert "RateApplicablePercent" not in xml_str
        assert (
            xml_str.count("<ram:CategoryCode>O</ram:CategoryCode>") == 3
        )  # 2 lines + 1 breakdown

    def test_br_o_09_breakdown_tax_amount_is_zero(self):
        breakdown = self._breakdowns(self._xml())[0]
        assert "<ram:CalculatedAmount>0.00</ram:CalculatedAmount>" in breakdown

    def test_br_o_10_breakdown_carries_exemption_reason(self):
        breakdown = self._breakdowns(self._xml())[0]
        assert (
            "<ram:ExemptionReasonCode>VATEX-EU-O</ram:ExemptionReasonCode>" in breakdown
        )
        assert (
            "<ram:ExemptionReason>Not subject to VAT</ram:ExemptionReason>" in breakdown
        )

    def test_totals_carry_no_tax(self):
        """Net 7200 with nothing added, against 8568 on the standard invoice."""
        xml_str = self._xml()
        assert (
            '<ram:TaxTotalAmount currencyID="EUR">0.00</ram:TaxTotalAmount>' in xml_str
        )
        assert "<ram:GrandTotalAmount>7200.000</ram:GrandTotalAmount>" in xml_str
        assert "8568" not in xml_str

    @pytest.mark.parametrize("profile", ["EN16931", "EXTENDED", "BASIC", "MINIMUM"])
    def test_schema_validation_all_profiles(self, profile):
        assert len(self._xml(profile=profile)) > 0

    def test_zero_rated_still_uses_category_z_with_a_rate(self):
        """Category O must not swallow the zero-rated case."""
        invoice = _make_invoice()
        invoice.contract.VAT_rate = Decimal("0")
        invoice.contract.VAT_category = TaxCategory.zero_rated
        for item in invoice.items:
            item.VAT_rate = Decimal("0")
            item.VAT_category = TaxCategory.zero_rated
        breakdown = self._breakdowns(self._xml(invoice=invoice))[0]
        assert "<ram:CategoryCode>Z</ram:CategoryCode>" in breakdown
        assert "<ram:RateApplicablePercent>0</ram:RateApplicablePercent>" in breakdown
        assert "VATEX-EU-O" not in breakdown

    def test_standard_invoice_is_unchanged(self):
        """Regression guard: the pre-existing S output must not shift."""
        xml_str = self._xml(invoice=_make_invoice())
        breakdown = self._breakdowns(xml_str)[0]
        assert "<ram:CategoryCode>S</ram:CategoryCode>" in breakdown
        assert (
            "<ram:RateApplicablePercent>19.00</ram:RateApplicablePercent>" in breakdown
        )
        assert "<ram:CalculatedAmount>1368.00</ram:CalculatedAmount>" in breakdown
        assert 'schemeID="VA"' in xml_str

    def test_zero_rated_and_outside_scope_lines_do_not_share_a_breakdown(self):
        """Both sit at 0%; keying the aggregate by rate alone would merge them."""
        invoice = _make_invoice()
        invoice.contract.VAT_rate = Decimal("0")
        for item, category in zip(
            invoice.items, [TaxCategory.zero_rated, TaxCategory.outside_scope]
        ):
            item.VAT_rate = Decimal("0")
            item.VAT_category = category

        user = _make_user()
        user.VAT_number = None  # BR-O-02, so the document still validates
        xml_str = serialize_zugferd_xml(
            invoice, user, profile="EN16931", validate=True
        ).decode("utf-8")

        breakdowns = self._breakdowns(xml_str)
        assert len(breakdowns) == 2
        categories = {
            re.search(r"<ram:CategoryCode>(\w)</ram:CategoryCode>", b).group(1)
            for b in breakdowns
        }
        assert categories == {"Z", "O"}


# -- Foreign-currency invoices: BT-6 / BT-111 ---------------------------------


class TestForeignCurrency:
    """EN16931 BR-53: with a tax currency code (BT-6), BT-111 must be present."""

    @staticmethod
    def _usd_invoice() -> Invoice:
        """A USD invoice to a US client — outside the scope of German VAT."""
        invoice = _make_outside_scope_invoice()
        invoice.contract.currency = "USD"
        return invoice

    def test_euro_invoice_emits_neither_bt6_nor_a_second_tax_total(self):
        xml_str = serialize_zugferd_xml(
            _make_invoice(), _make_user(), profile="EN16931", validate=True
        ).decode("utf-8")
        assert "TaxCurrencyCode" not in xml_str
        assert len(re.findall(r"<ram:TaxTotalAmount", xml_str)) == 1

    def test_usd_invoice_emits_bt6_and_bt111_in_the_tax_currency(self):
        user = _make_user()
        user.operating_country = "Germany"
        xml_str = serialize_zugferd_xml(
            self._usd_invoice(), user, profile="EN16931", validate=True
        ).decode("utf-8")

        assert "<ram:InvoiceCurrencyCode>USD</ram:InvoiceCurrencyCode>" in xml_str
        assert "<ram:TaxCurrencyCode>EUR</ram:TaxCurrencyCode>" in xml_str
        # Outside the scope of VAT: zero VAT, so BT-111 is 0.00 and needs no rate.
        assert (
            '<ram:TaxTotalAmount currencyID="EUR">0.00</ram:TaxTotalAmount>' in xml_str
        )
