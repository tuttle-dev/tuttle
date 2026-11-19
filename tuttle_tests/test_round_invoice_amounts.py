"""Invoice amounts are rounded half-up to the cent, so every document adds up.

Each line multiplies out to the cent it charges, the lines sum to the
subtotal, and VAT is rounded once per tax category and rate, as EN16931
calculates it. The PDF, the app and the e-invoice XML show the same figures.
"""

import datetime
import re
from decimal import ROUND_HALF_UP, Decimal

import pandas
import pytest
from lxml import etree
from sqlmodel import Session, SQLModel, create_engine

from tuttle import invoicing, rendering, timetracking
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.data_source import InvoicingDataSource
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.app.preferences.model import INVOICE_TEMPLATES
from tuttle.einvoice import serialize_zugferd_xml
from tuttle.model import (
    Address,
    BankAccount,
    Client,
    Contract,
    ContractCharge,
    Invoice,
    InvoiceItem,
    PaymentMilestone,
    Project,
    User,
)
from tuttle.time import ChargeBasis, ContractType, Cycle, TimeUnit

#: 1 h 20 min as an hour quantity, the way invoices created before rounding stored it.
LONG_QUANTITY = 1.3333333333333333


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


def _contract(unit: TimeUnit = TimeUnit.hour, rate: str = "95.00") -> Contract:
    return Contract(
        title="Boiler Maintenance",
        client=Client(
            name="Sam Lowry",
            address=Address(street="Shangrila Towers", number="1", postal_code="10115", city="Berlin", country="Germany"),
        ),
        start_date=datetime.date(2026, 1, 1),
        rate=Decimal(rate),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=unit,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )


def _invoice(*lines, reminder_fee=None) -> Invoice:
    """An invoice with one line per ``(quantity, unit price, VAT rate)``."""
    invoice = Invoice(number="2026-001", date=datetime.date(2026, 4, 1), contract=_contract(), reminder_fee=reminder_fee)
    for quantity, unit_price, vat_rate in lines:
        InvoiceItem(
            invoice=invoice,
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 3, 31),
            quantity=quantity,
            unit="hour",
            unit_price=Decimal(unit_price),
            VAT_rate=Decimal(vat_rate),
            description="Boiler service",
        )
    return invoice


# -- The model ----------------------------------------------------------------


class TestInvoiceArithmetic:
    def test_a_line_charges_quantity_times_price_rounded_half_up(self):
        """0.25 h at 12.50 is 3.125, billed as 3.13."""
        assert _invoice((0.25, "12.50", "0.19")).items[0].subtotal == Decimal("3.13")

    def test_the_subtotal_is_the_sum_of_the_lines(self):
        """126.67 + 26.67 = 153.34, not the 153.33 the unrounded lines sum to."""
        invoice = _invoice((LONG_QUANTITY, "95.00", "0.19"), (LONG_QUANTITY, "20.00", "0.19"))
        assert [item.subtotal for item in invoice.items] == [Decimal("126.67"), Decimal("26.67")]
        assert invoice.sum == Decimal("153.34")

    def test_vat_rounds_half_up(self):
        """5% of 0.50 is 0.025: 0.03, where banker's rounding would give 0.02."""
        assert _invoice((1, "0.50", "0.05")).VAT_total == Decimal("0.03")

    def test_vat_is_rounded_once_per_rate_not_per_line(self):
        """19% of 10.10 is 1.92 and 7% of 10.10 is 0.71, so 2.63 in all;
        rounding each line's VAT would give 1.91 + 0.01 + 0.70 + 0.00 = 2.62."""
        invoice = _invoice(
            (1, "10.05", "0.19"),
            (1, "0.05", "0.19"),
            (1, "10.05", "0.07"),
            (1, "0.05", "0.07"),
        )
        assert [(e.rate, e.taxable_amount, e.tax_amount) for e in invoice.vat_breakdown] == [
            (Decimal("0.19"), Decimal("10.10"), Decimal("1.92")),
            (Decimal("0.07"), Decimal("10.10"), Decimal("0.71")),
        ]
        assert invoice.VAT_total == Decimal("2.63")

    def test_lines_vat_shares_add_up_to_the_vat_before_rounding(self):
        invoice = _invoice((1, "10.05", "0.19"), (1, "0.05", "0.19"))
        assert sum(item.VAT for item in invoice.items) == Decimal("1.919")
        assert invoice.VAT_total == Decimal("1.92")

    def test_the_total_is_subtotal_plus_vat(self):
        """3.13 + 0.59, where the unrounded total was 3.715."""
        invoice = _invoice((0.25, "12.50", "0.19"))
        assert (invoice.sum, invoice.VAT_total, invoice.total) == (Decimal("3.13"), Decimal("0.59"), Decimal("3.72"))

    def test_a_reminder_fee_adds_to_the_total(self):
        assert _invoice((0.25, "12.50", "0.19"), reminder_fee=Decimal("5.00")).total == Decimal("8.72")

    def test_an_empty_invoice_totals_zero_cents(self):
        invoice = _invoice()
        assert str(invoice.sum) == str(invoice.VAT_total) == str(invoice.total) == "0.00"

    def test_a_milestone_share_rounds_half_up(self):
        """50% of 1,000.01 is 500.005: 500.01."""
        contract = _contract()
        contract.type = ContractType.fixed_price
        contract.fixed_price = Decimal("1000.01")
        milestone = PaymentMilestone(title="Instalment 1", percentage=Decimal("50"), position=0)
        assert invoicing.milestone_amount(milestone, contract) == Decimal("500.01")


# -- Invoices from tracked time -----------------------------------------------


def _project(unit: TimeUnit = TimeUnit.hour, rate: str = "95.00", charges=()) -> Project:
    contract = _contract(unit, rate)
    contract.charges = list(charges)
    return Project(
        title="Boiler Maintenance",
        tag="#boiler",
        contract=contract,
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 31),
    )


def _timesheet(project: Project, *spans: tuple[str, str]):
    """A March timesheet of the ``(begin, end)`` spans tracked for ``project``."""
    begins = pandas.to_datetime([begin for begin, _ in spans])
    ends = pandas.to_datetime([end for _, end in spans])
    data = pandas.DataFrame(
        {
            "begin": begins,
            "end": ends,
            "title": ["Boiler service"] * len(spans),
            "tag": [project.tag] * len(spans),
            "description": [""] * len(spans),
            "all_day": [False] * len(spans),
        }
    )
    data["duration"] = data["end"] - data["begin"]
    return timetracking.generate_timesheet(
        data.set_index("begin"), project, datetime.date(2026, 3, 1), datetime.date(2026, 3, 31)
    )


def _generate(project: Project, *timesheets) -> Invoice:
    return invoicing.generate_invoice(
        list(timesheets),
        project.contract,
        project,
        number="2026-001",
        date=datetime.date(2026, 4, 1),
        charges=project.contract.charges,
    )


class TestTrackedTimeIsBilledToTwoDecimals:
    def test_hours(self):
        """1 h 20 min bills 1.33 h, and 1.33 × 95.00 = 126.35."""
        project = _project()
        invoice = _generate(project, _timesheet(project, ("2026-03-02 09:00", "2026-03-02 10:20")))
        assert invoice.items[0].quantity == 1.33
        assert invoice.items[0].subtotal == Decimal("126.35")

    def test_the_quantity_rounds_half_up(self):
        """7 min 30 s is 0.125 h: 0.13 h."""
        project = _project()
        invoice = _generate(project, _timesheet(project, ("2026-03-02 09:00:00", "2026-03-02 09:07:30")))
        assert invoice.items[0].quantity == 0.13

    def test_days(self):
        """7 h 10 min of an 8-hour day is 0.8958… days: 0.9 days, 684.00 at 760.00."""
        project = _project(TimeUnit.day, rate="760.00")
        invoice = _generate(project, _timesheet(project, ("2026-03-02 09:00", "2026-03-02 16:10")))
        assert invoice.items[0].quantity == 0.9
        assert invoice.items[0].subtotal == Decimal("684.00")

    def test_a_per_unit_charge_mirrors_the_billed_quantity(self):
        """Two timesheets of 1 h 20 min bill 1.33 h each, so the allowance bills 2.66 h."""
        allowance = ContractCharge(id=1, description="Travel allowance", amount=Decimal("20.00"), basis=ChargeBasis.per_unit)
        project = _project(charges=[allowance])
        invoice = _generate(
            project,
            _timesheet(project, ("2026-03-02 09:00", "2026-03-02 10:20")),
            _timesheet(project, ("2026-03-09 09:00", "2026-03-09 10:20")),
        )
        assert [item.quantity for item in invoice.items] == [1.33, 1.33, 2.66]
        assert [item.subtotal for item in invoice.items] == [Decimal("126.35"), Decimal("126.35"), Decimal("53.20")]
        assert invoice.sum == Decimal("305.90")


# -- The documents ------------------------------------------------------------


def _render(invoice: Invoice, template_name: str = "invoice-modern", language: str = "en") -> str:
    return rendering.render_invoice(
        user=_user(),
        invoice=invoice,
        out_dir=None,
        document_format="html",
        template_name=template_name,
        language=language,
    )


def _cells(html: str, column: str) -> list[str]:
    """The text of each line item's cell in ``column``, e.g. "col-qty"."""
    return [text.strip() for text in re.findall(rf'<td class="{column}[^"]*">([^<]*)</td>', html)]


class TestDocumentsShowRoundedQuantities:
    @pytest.mark.parametrize("template_name", list(INVOICE_TEMPLATES))
    def test_quantities_have_at_most_two_decimals(self, template_name):
        invoice = _invoice((LONG_QUANTITY, "95.00", "0.19"), (8.0, "95.00", "0.19"), (0.5, "95.00", "0.19"))
        assert _cells(_render(invoice, template_name), "col-qty") == ["1.33", "8", "0.5"]

    def test_quantities_are_formatted_in_the_document_language(self):
        invoice = _invoice((LONG_QUANTITY, "95.00", "0.19"), (1250.0, "1.00", "0.19"))
        assert _cells(_render(invoice, language="de"), "col-qty") == ["1,33", "1.250"]

    def test_the_unit_agrees_with_the_printed_quantity(self):
        """A stored 1.0000001 h prints as 1, so the unit reads "hour"."""
        html = _render(_invoice((1.0000001, "95.00", "0.19")))
        assert _cells(html, "col-qty") == ["1"]
        assert _cells(html, "col-unit") == ["hour"]

    def test_the_printed_lines_add_up_to_the_printed_totals(self):
        invoice = _invoice((LONG_QUANTITY, "95.00", "0.19"), (LONG_QUANTITY, "20.00", "0.19"))
        html = _render(invoice)

        def euros(text: str) -> Decimal:
            return Decimal(text.replace("€", "").replace(",", ""))

        lines = [euros(text) for text in _cells(html, "col-subtotal")]
        subtotal, vat, total_due = (euros(text) for text in re.findall(r'class="totals-amount">([^<]*)<', html))
        assert sum(lines) == subtotal == Decimal("153.34")
        assert subtotal + vat == total_due == invoice.total

    def test_the_app_shows_the_quantity_as_the_invoice_does(self):
        invoice = _invoice((LONG_QUANTITY, "95.00", "0.19"), (8.0, "95.00", "0.19"), (0.5, "95.00", "0.19"))
        assert [item.quantity_formatted for item in invoice.items] == ["1.33", "8", "0.5"]
        assert invoice.items[0].to_rpc_dict()["quantity_formatted"] == "1.33"


# -- The e-invoice ------------------------------------------------------------

NS = {
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
}

AMOUNT_TAGS = [
    "ChargeAmount",
    "LineTotalAmount",
    "ChargeTotalAmount",
    "AllowanceTotalAmount",
    "TaxBasisTotalAmount",
    "TaxTotalAmount",
    "GrandTotalAmount",
    "TotalPrepaidAmount",
    "DuePayableAmount",
    "BasisAmount",
    "CalculatedAmount",
]


def _xml(invoice: Invoice) -> etree._Element:
    return etree.fromstring(serialize_zugferd_xml(invoice, _user(), profile="EN16931"))


def _texts(xml: etree._Element, path: str) -> list[str]:
    return [element.text for element in xml.iterfind(path, NS)]


def _amounts(xml: etree._Element, path: str) -> list[Decimal]:
    return [Decimal(text) for text in _texts(xml, path)]


def _assert_amounts_have_two_decimals(xml: etree._Element):
    """EN16931 BR-DEC: at most two decimals; Tuttle always writes exactly two."""
    amounts = [text for tag in AMOUNT_TAGS for text in _texts(xml, f".//ram:{tag}")]
    assert amounts
    assert [a for a in amounts if not re.fullmatch(r"-?\d+\.\d\d", a)] == []


class TestEInvoiceAmounts:
    @staticmethod
    def _time_invoice() -> Invoice:
        return _invoice(
            (LONG_QUANTITY, "95.00", "0.19"),
            (7.166666666666667, "95.00", "0.19"),
            (10.0, "80.00", "0.19"),
            (2.5, "35.00", "0.07"),
        )

    def test_every_amount_has_two_decimals(self):
        _assert_amounts_have_two_decimals(_xml(self._time_invoice()))

    def test_quantities_have_at_most_four_decimals(self):
        xml = _xml(self._time_invoice())
        assert _texts(xml, ".//ram:BilledQuantity") == ["1.3333", "7.1667", "10", "2.5"]

    def test_a_sub_cent_price_is_not_rounded_away(self):
        """EN16931 limits the decimals of amounts, not of prices."""
        xml = _xml(_invoice((100, "0.125", "0.19"), (1, "80.0000000000", "0.19")))
        assert _texts(xml, ".//ram:NetPriceProductTradePrice/ram:ChargeAmount") == ["0.125", "80.00"]

    def test_the_en16931_sums_hold_exactly(self):
        invoice = self._time_invoice()
        xml = _xml(invoice)
        summation = ".//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:"
        line_totals = _amounts(xml, ".//ram:IncludedSupplyChainTradeLineItem//ram:LineTotalAmount")
        (line_total,) = _amounts(xml, summation + "LineTotalAmount")
        (tax_basis,) = _amounts(xml, summation + "TaxBasisTotalAmount")
        (tax_total,) = _amounts(xml, summation + "TaxTotalAmount")
        (grand_total,) = _amounts(xml, summation + "GrandTotalAmount")
        (due,) = _amounts(xml, summation + "DuePayableAmount")
        breakdowns = list(xml.iterfind(".//ram:ApplicableHeaderTradeSettlement/ram:ApplicableTradeTax", NS))

        assert sum(line_totals) == line_total  # BR-CO-10
        assert tax_basis == line_total  # BR-CO-13, no allowances or charges
        assert sum(Decimal(b.findtext("ram:CalculatedAmount", namespaces=NS)) for b in breakdowns) == tax_total  # BR-CO-14
        assert grand_total == tax_basis + tax_total  # BR-CO-15
        assert due == grand_total  # BR-CO-16, nothing prepaid
        for breakdown in breakdowns:  # BR-CO-17
            basis = Decimal(breakdown.findtext("ram:BasisAmount", namespaces=NS))
            percent = Decimal(breakdown.findtext("ram:RateApplicablePercent", namespaces=NS))
            calculated = Decimal(breakdown.findtext("ram:CalculatedAmount", namespaces=NS))
            assert calculated == (basis * percent / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def test_the_grand_total_is_the_total_on_the_pdf(self):
        invoice = self._time_invoice()
        (grand_total,) = _texts(_xml(invoice), ".//ram:GrandTotalAmount")
        assert grand_total == str(invoice.total)
        assert f"€{invoice.total:,}" in _render(invoice)


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


class TestReloadedDepositAndFinalInvoices:
    """The database hands amounts back as e.g. 5000.0000000000; the XML must not."""

    @staticmethod
    def _schedule(engine) -> tuple[int, list[int]]:
        with Session(engine) as session:
            session.add(_user())
            contract = _contract()
            contract.type = ContractType.fixed_price
            contract.rate = None
            contract.fixed_price = Decimal("10000")
            contract.payment_milestones = [
                PaymentMilestone(title=f"Instalment {position + 1}", percentage=Decimal(pct), position=position)
                for position, pct in enumerate(["33.33", "33.33", "33.34"])
            ]
            project = Project(
                title="Heating Overhaul",
                description="Ductwork",
                tag="#overhaul",
                contract=contract,
                start_date=datetime.date(2026, 1, 1),
                end_date=datetime.date(2026, 12, 31),
            )
            session.add(project)
            session.commit()
            return project.id, [m.id for m in contract.payment_milestones]

    def test_deposits_and_final_serialise_amounts_with_two_decimals(self, in_memory_db):
        project_id, milestone_ids = self._schedule(in_memory_db)
        intent = InvoicingIntent()
        created = [intent.create_deposit(project_id, mid, datetime.date(2026, 2, 1)) for mid in milestone_ids]
        assert all(result.was_intent_successful for result in created), [r.error_msg for r in created]

        data_source = InvoicingDataSource()
        documents = [data_source.get_invoice_by_id(result.data.id).data for result in created]
        final = next(doc for doc in documents if doc.is_final_invoice)
        for document in documents:
            _assert_amounts_have_two_decimals(_xml(document))

        xml = _xml(final)
        (due,) = _texts(xml, ".//ram:DuePayableAmount")
        assert due == str(final.remaining_balance)


class TestTypedQuantities:
    """A quantity typed into a manual line is billed to two decimals as well."""

    @staticmethod
    def _project(engine) -> Project:
        with Session(engine) as session:
            session.add(_user())
            project = Project(
                title="Boiler Service",
                description="Annual service",
                tag="#service",
                contract=_contract(),
                start_date=datetime.date(2026, 1, 1),
            )
            session.add(project)
            session.commit()
            project_id = project.id
        return InvoicingIntent()._projects_intent.get_by_id(project_id).data

    def test_a_typed_quantity_is_billed_as_the_document_shows_it(self, in_memory_db):
        project = self._project(in_memory_db)
        result = InvoicingIntent().create_invoice(
            datetime.date(2026, 3, 31),
            project,
            datetime.date(2026, 3, 1),
            datetime.date(2026, 3, 31),
            render=False,
            manual_items=[{"description": "Repairs", "quantity": 1.3333, "unit": "hour", "unit_price": "95.00"}],
        )
        assert result.was_intent_successful, result.error_msg
        (item,) = result.data.items
        assert item.quantity == 1.33
        assert item.subtotal == Decimal("126.35")
