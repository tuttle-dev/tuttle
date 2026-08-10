"""Tests for the invoice module."""

import datetime
from decimal import Decimal

import faker
import pandas
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle import demo, invoicing, rendering, timetracking
from tuttle.calendar import get_month_start_end
from tuttle.model import (
    Address,
    BankAccount,
    Client,
    Contract,
    ContractCharge,
    Invoice,
    InvoiceItem,
    InvoiceNote,
    Project,
    TaxCategory,
)
from tuttle.time import ChargeBasis, ContractType, Cycle, TimeUnit


def test_invoice():
    the_invoice = Invoice(
        number="27B-6",
        date=datetime.date.today(),
        sent=True,
        paid=False,
        cancelled=False,
    )

    item_1 = InvoiceItem(
        invoice=the_invoice,
        start_date=datetime.date.today(),
        end_date=datetime.date.today(),
        quantity=10,
        unit="hours",
        unit_price=Decimal(50),
        description="work work",
        VAT_rate=Decimal(0.20),
    )

    item_2 = InvoiceItem(
        invoice=the_invoice,
        start_date=datetime.date.today(),
        end_date=datetime.date.today(),
        quantity=10,
        unit="hours",
        unit_price=Decimal(100),
        description="work work",
        VAT_rate=Decimal(0.20),
    )

    assert item_1.invoice == the_invoice
    assert item_2.invoice == the_invoice

    assert the_invoice.sum == Decimal(1500)
    assert the_invoice.VAT_total == Decimal(300)
    assert the_invoice.total == Decimal(1800)


def test_generate_invoice(
    demo_projects,
    demo_calendar_timetracking,
):
    for i, project in enumerate(demo_projects):
        timesheets = []
        for period in ["January 2022", "February 2022"]:
            period_start, period_end = get_month_start_end(period)
            try:
                timesheet = timetracking.generate_timesheet(
                    timetracking_data=demo_calendar_timetracking.to_data(),
                    project=project,
                    period_start=period_start,
                    period_end=period_end,
                    item_description=project.title,
                )
            except ValueError:
                continue
            if not timesheet.empty:
                timesheets.append(timesheet)
        if not timesheets:
            continue
        invoice = invoicing.generate_invoice(
            timesheets=timesheets,
            contract=project.contract,
            project=project,
            date=datetime.date.today(),
            number=f"{datetime.date.today().strftime('%Y-%m-%d')}-{i}",
        )
        # Regression: previously every assertion in this test was commented out,
        # so a totally broken generate_invoice would pass.  Now we check that the
        # output actually reflects the input.
        assert len(invoice.items) == len(timesheets)
        assert invoice.sum == sum(item.subtotal for item in invoice.items)
        assert all(item.unit == project.contract.unit.value for item in invoice.items)
        if Decimal(str(project.contract.rate)) > 0:
            assert invoice.sum > 0
            assert invoice.total > 0


# ---------------------------------------------------------------------------
# Per-unit regression tests for Bug A (generate_invoice ignored contract.unit)
# ---------------------------------------------------------------------------


def _build_project(unit: TimeUnit, rate, tag: str) -> Project:
    client = Client(
        name="Acme Co",
        address=Address(
            street="Main",
            number="1",
            postal_code="00000",
            city="Nowhere",
            country="N/A",
        ),
    )
    contract = Contract(
        title="Test Contract",
        client=client,
        signature_date=datetime.date(2022, 1, 1),
        start_date=datetime.date(2022, 1, 1),
        rate=rate,
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=unit,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Project(
        title=f"Test Project {tag}",
        description="Project for unit-test coverage",
        tag=tag,
        contract=contract,
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 12, 31),
    )


def _synthetic_timetracking_data(tag: str) -> pandas.DataFrame:
    """8 hours of tracked time across two work blocks."""
    data = {
        "begin": pandas.to_datetime(["2022-01-03 09:00:00", "2022-01-03 13:00:00"]),
        "end": pandas.to_datetime(["2022-01-03 13:00:00", "2022-01-03 17:00:00"]),
        "title": ["Morning", "Afternoon"],
        "tag": [tag, tag],
        "description": ["", ""],
        "all_day": [False, False],
    }
    df = pandas.DataFrame(data)
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


def test_generate_invoice_respects_hour_unit():
    """8h tracked on an hour-rate contract → quantity=8, subtotal=400."""
    project = _build_project(TimeUnit.hour, Decimal("50"), tag="#HourProj")
    data = _synthetic_timetracking_data(project.tag)

    timesheet = timetracking.generate_timesheet(
        timetracking_data=data,
        project=project,
        period_start=datetime.date(2022, 1, 1),
        period_end=datetime.date(2022, 1, 31),
    )
    invoice = invoicing.generate_invoice(
        timesheets=[timesheet],
        contract=project.contract,
        project=project,
        number="HOUR-001",
        date=datetime.date(2022, 2, 1),
    )

    assert len(invoice.items) == 1
    item = invoice.items[0]
    assert item.quantity == pytest.approx(8.0)
    assert item.unit == "hour"
    assert item.unit_price == Decimal("50")
    assert invoice.sum == Decimal("400")


def test_generate_invoice_respects_day_unit():
    """8h tracked on a day-rate contract (8h/workday) → quantity=1.0, subtotal=500.

    This is the Bug-A reproducer: previously total_hours was used verbatim with
    unit hardcoded to ``"hour"``, producing 8 × €500 = €4000 instead of €500.
    """
    project = _build_project(TimeUnit.day, Decimal("500"), tag="#DayProj")
    data = _synthetic_timetracking_data(project.tag)

    timesheet = timetracking.generate_timesheet(
        timetracking_data=data,
        project=project,
        period_start=datetime.date(2022, 1, 1),
        period_end=datetime.date(2022, 1, 31),
    )
    invoice = invoicing.generate_invoice(
        timesheets=[timesheet],
        contract=project.contract,
        project=project,
        number="DAY-001",
        date=datetime.date(2022, 2, 1),
    )

    assert len(invoice.items) == 1
    item = invoice.items[0]
    # A contractual "day" is units_per_workday=8 hours, so 8h tracked = 1.0 day.
    assert item.quantity == pytest.approx(1.0)
    assert item.unit == "day"
    assert invoice.sum == Decimal("500")


# ---------------------------------------------------------------------------
# Fixed-price contracts
# ---------------------------------------------------------------------------


def _build_fixed_price_project(fixed_price, tag: str) -> Project:
    client = Client(
        name="FixedCo",
        address=Address(
            street="Main",
            number="1",
            postal_code="00000",
            city="Nowhere",
            country="N/A",
        ),
    )
    contract = Contract(
        title="Fixed Price Contract",
        client=client,
        start_date=datetime.date(2022, 1, 1),
        type=ContractType.fixed_price,
        fixed_price=fixed_price,
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        billing_cycle=Cycle.monthly,
    )
    return Project(
        title=f"Fixed Project {tag}",
        description="Fixed-price project",
        tag=tag,
        contract=contract,
        start_date=datetime.date(2022, 1, 1),
        end_date=datetime.date(2022, 12, 31),
    )


class TestFixedPriceInvoicing:
    """Business-level tests for fixed-price contracts and invoicing."""

    def test_fixed_price_project_bills_agreed_amount(self):
        """Invoicing a fixed-price project charges the full agreed amount."""
        project = _build_fixed_price_project(Decimal("4500"), tag="#FPBill")
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="FP-001",
            date=datetime.date(2022, 2, 1),
        )
        assert invoice.sum == Decimal("4500")
        assert invoice.total == Decimal("5355.00")  # 4500 + 19% VAT

    def test_fixed_price_invoice_has_single_line_item(self):
        """A fixed-price invoice contains exactly one lump-sum line."""
        project = _build_fixed_price_project(Decimal("10000"), tag="#FPSingle")
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="FP-002",
            date=datetime.date(2022, 3, 1),
        )
        assert len(invoice.items) == 1

    def test_project_knows_it_is_fixed_price(self):
        """A project with a fixed-price contract exposes that fact."""
        project = _build_fixed_price_project(Decimal("3000"), tag="#FPFlag")
        assert project.is_fixed_price

    def test_time_based_project_is_not_fixed_price(self):
        """A project with a rate-based contract is not fixed-price."""
        client = Client(
            name="HourlyCo",
            address=Address(
                street="Clock St",
                number="2",
                postal_code="11111",
                city="Timeville",
                country="N/A",
            ),
        )
        contract = Contract(
            title="Hourly Contract",
            client=client,
            start_date=datetime.date(2022, 1, 1),
            rate=Decimal("100"),
            currency="EUR",
            VAT_rate=Decimal("0.19"),
            billing_cycle=Cycle.monthly,
        )
        project = Project(
            title="Hourly Project",
            description="Time-based project",
            tag="#HourlyProj",
            contract=contract,
            start_date=datetime.date(2022, 1, 1),
            end_date=datetime.date(2022, 12, 31),
        )
        assert not project.is_fixed_price

    def test_vat_applied_correctly_to_fixed_price(self):
        """VAT is computed on top of the fixed price, not included in it."""
        project = _build_fixed_price_project(Decimal("1000"), tag="#FPVAT")
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="FP-003",
            date=datetime.date(2022, 4, 1),
        )
        assert invoice.VAT_total == Decimal("190.00")
        assert invoice.total == Decimal("1190.00")


# ---------------------------------------------------------------------------
# Additional contract charges
# ---------------------------------------------------------------------------


def _tracked_hours(tag: str, hours: int) -> pandas.DataFrame:
    """One tracked block of *hours* hours, starting 2022-01-03 09:00."""
    begin = pandas.to_datetime(["2022-01-03 09:00:00"])
    df = pandas.DataFrame(
        {
            "begin": begin,
            "end": begin + pandas.Timedelta(hours=hours),
            "title": ["Retrofit work"],
            "tag": [tag],
            "description": [""],
            "all_day": [False],
        }
    )
    df["duration"] = df["end"] - df["begin"]
    return df.set_index("begin")


def _day_rate_project_with_charges(*charges: ContractCharge, tag: str) -> Project:
    """A €500/day contract (8h workday) carrying the given charges."""
    project = _build_project(TimeUnit.day, Decimal("500"), tag=tag)
    project.contract.charges = list(charges)
    return project


def _invoice_for(project: Project, hours: int, charges=None) -> Invoice:
    timesheet = timetracking.generate_timesheet(
        timetracking_data=_tracked_hours(project.tag, hours),
        project=project,
        period_start=datetime.date(2022, 1, 1),
        period_end=datetime.date(2022, 1, 31),
    )
    return invoicing.generate_invoice(
        timesheets=[timesheet],
        contract=project.contract,
        project=project,
        number="CHG-001",
        date=datetime.date(2022, 2, 1),
        charges=charges,
    )


class TestPerUnitCharges:
    """A per-unit charge is billed in lockstep with the tracked time."""

    def test_daily_fee_mirrors_billed_days(self):
        """The headline case: 3 days worked bills 3 day rates and 3 daily fees."""
        project = _day_rate_project_with_charges(
            ContractCharge(description="Daily allowance", amount=Decimal("80")),
            tag="#DailyFee",
        )
        invoice = _invoice_for(project, hours=24)

        assert len(invoice.items) == 2
        work, fee = invoice.items
        assert work.quantity == pytest.approx(3.0)
        assert work.unit_price == Decimal("500")
        assert fee.quantity == pytest.approx(3.0)
        assert fee.unit == "day"
        assert fee.unit_price == Decimal("80")
        assert fee.description == "Daily allowance"
        assert invoice.sum == Decimal("1740")  # 3 × 500 + 3 × 80

    def test_fractional_days_carry_fractional_fees(self):
        """A fee mirrors the billed quantity exactly, fractions included."""
        project = _day_rate_project_with_charges(
            ContractCharge(description="Daily allowance", amount=Decimal("80")),
            tag="#FracFee",
        )
        invoice = _invoice_for(project, hours=20)

        work, fee = invoice.items
        assert work.quantity == pytest.approx(2.5)
        assert fee.quantity == pytest.approx(2.5)
        assert invoice.sum == Decimal("1450")  # 2.5 × 500 + 2.5 × 80

    def test_charge_inherits_contract_tax_treatment(self):
        project = _day_rate_project_with_charges(
            ContractCharge(description="Daily allowance", amount=Decimal("80")),
            tag="#FeeVAT",
        )
        project.contract.VAT_category = TaxCategory.standard
        fee = _invoice_for(project, hours=8).items[1]

        assert fee.VAT_rate == Decimal("0.19")
        assert fee.VAT_category is TaxCategory.standard


class TestFlatCharges:
    """Charges that are not derived from tracked time bill a single unit."""

    def test_per_invoice_charge_ignores_tracked_time(self):
        project = _day_rate_project_with_charges(
            ContractCharge(description="Handling fee", amount=Decimal("25"), basis=ChargeBasis.per_invoice),
            tag="#Handling",
        )
        invoice = _invoice_for(project, hours=24)

        fee = invoice.items[1]
        assert fee.quantity == pytest.approx(1.0)
        assert fee.unit == "flat"
        assert invoice.sum == Decimal("1525")  # 3 × 500 + 25

    def test_charges_keep_their_configured_order(self):
        project = _day_rate_project_with_charges(
            ContractCharge(description="Second", amount=Decimal("10"), basis=ChargeBasis.per_invoice, position=1),
            ContractCharge(description="First", amount=Decimal("20"), basis=ChargeBasis.per_invoice, position=0),
            tag="#Ordered",
        )
        invoice = _invoice_for(project, hours=8)

        assert [item.description for item in invoice.items[1:]] == ["First", "Second"]

    def test_once_charge_is_left_out_when_history_is_unknown(self):
        """Without a caller-supplied list, a one-time charge is withheld.

        ``generate_invoice`` cannot see earlier invoices, and billing a setup
        fee twice is worse than billing it late.
        """
        project = _day_rate_project_with_charges(
            ContractCharge(description="Setup fee", amount=Decimal("450"), basis=ChargeBasis.once),
            tag="#OnceUnknown",
        )
        invoice = _invoice_for(project, hours=8)

        assert len(invoice.items) == 1

    def test_once_charge_is_billed_when_the_caller_supplies_it(self):
        project = _day_rate_project_with_charges(
            ContractCharge(description="Setup fee", amount=Decimal("450"), basis=ChargeBasis.once),
            tag="#OnceGiven",
        )
        invoice = _invoice_for(project, hours=8, charges=project.contract.charges)

        assert [item.description for item in invoice.items][1:] == ["Setup fee"]
        assert invoice.items[1].quantity == pytest.approx(1.0)

    def test_inactive_charges_are_skipped(self):
        project = _day_rate_project_with_charges(
            ContractCharge(description="Retired fee", amount=Decimal("99"), is_active=False),
            tag="#Inactive",
        )
        assert len(_invoice_for(project, hours=8).items) == 1

    def test_fixed_price_invoice_carries_flat_charges(self):
        project = _build_fixed_price_project(Decimal("4500"), tag="#FPCharge")
        project.contract.charges = [
            ContractCharge(description="Handling fee", amount=Decimal("50"), basis=ChargeBasis.per_invoice),
        ]
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="FP-CHG",
            date=datetime.date(2022, 2, 1),
        )

        assert len(invoice.items) == 2
        assert invoice.sum == Decimal("4550")


class TestChargeValidation:
    """``Contract.validate_charges`` is the single gate on every write path."""

    def test_per_unit_charge_rejected_on_fixed_price_contract(self):
        project = _build_fixed_price_project(Decimal("4500"), tag="#FPPerUnit")
        project.contract.charges = [
            ContractCharge(description="Daily allowance", amount=Decimal("80"), basis=ChargeBasis.per_unit),
        ]
        with pytest.raises(ValueError, match="per unit"):
            project.contract.validate_charges()

    def test_charge_needs_a_description(self):
        project = _build_project(TimeUnit.day, Decimal("500"), tag="#NoDesc")
        project.contract.charges = [ContractCharge(description="  ", amount=Decimal("80"))]
        with pytest.raises(ValueError, match="description"):
            project.contract.validate_charges()

    @pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-5")])
    def test_charge_needs_a_positive_amount(self, amount):
        project = _build_project(TimeUnit.day, Decimal("500"), tag="#BadAmount")
        project.contract.charges = [ContractCharge(description="Allowance", amount=amount)]
        with pytest.raises(ValueError, match="greater than zero"):
            project.contract.validate_charges()

    def test_valid_charges_pass(self):
        project = _day_rate_project_with_charges(
            ContractCharge(description="Daily allowance", amount=Decimal("80")),
            ContractCharge(description="Setup fee", amount=Decimal("450"), basis=ChargeBasis.once),
            tag="#Valid",
        )
        project.contract.validate_charges()


# ---------------------------------------------------------------------------
# Invoice notes
# ---------------------------------------------------------------------------


class TestInvoiceNoteModel:
    """InvoiceNote can be stored and retrieved."""

    def test_store_and_retrieve(self):
        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        note = InvoiceNote(text="Thank you for your prompt payment.")
        with Session(engine) as session:
            session.add(note)
            session.commit()
            session.refresh(note)
            assert note.id is not None
            assert note.created_at is not None
        with Session(engine) as session:
            retrieved = session.exec(select(InvoiceNote)).first()
            assert retrieved.text == "Thank you for your prompt payment."

    def test_created_at_defaults_to_now(self):
        before = datetime.datetime.now()
        note = InvoiceNote(text="test")
        after = datetime.datetime.now()
        assert before <= note.created_at <= after


class TestInvoiceNotesField:
    """Invoice.notes optional field."""

    def test_defaults_to_none(self):
        inv = Invoice(
            number="N-001",
            date=datetime.date.today(),
        )
        assert inv.notes is None

    def test_custom_notes_roundtrip(self):
        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        inv = Invoice(
            number="N-002",
            date=datetime.date.today(),
            notes="We appreciate your continued partnership.",
        )
        with Session(engine) as session:
            session.add(inv)
            session.commit()
            session.refresh(inv)
        with Session(engine) as session:
            loaded = session.exec(select(Invoice)).first()
            assert loaded.notes == "We appreciate your continued partnership."


@pytest.fixture()
def notes_intent(tmp_path, monkeypatch):
    """Provide an InvoiceNotesIntent wired to a throwaway SQLite DB."""
    import tuttle.app.core.abstractions as _abs
    from tuttle.app.invoice_notes.intent import InvoiceNotesIntent

    db_path = tmp_path / "test.db"
    monkeypatch.setattr(_abs, "_active_db_path", db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    return InvoiceNotesIntent()


class TestInvoiceNotesIntent:
    """CRUD via InvoiceNotesIntent."""

    def test_create_returns_note(self, notes_intent):
        result = notes_intent.create("Please pay within 30 days.")
        assert result.was_intent_successful
        assert result.data.text == "Please pay within 30 days."

    def test_create_strips_whitespace(self, notes_intent):
        result = notes_intent.create("  padded  ")
        assert result.was_intent_successful
        assert result.data.text == "padded"

    def test_create_empty_text_fails(self, notes_intent):
        result = notes_intent.create("")
        assert not result.was_intent_successful

    def test_create_whitespace_only_fails(self, notes_intent):
        result = notes_intent.create("   ")
        assert not result.was_intent_successful

    def test_create_deduplicates(self, notes_intent):
        r1 = notes_intent.create("Unique note")
        r2 = notes_intent.create("Unique note")
        assert r1.data.text == r2.data.text

    def test_get_all_empty(self, notes_intent):
        result = notes_intent.get_all()
        assert result.was_intent_successful
        assert result.data == []

    def test_get_all_returns_created(self, notes_intent):
        notes_intent.create("Note A")
        notes_intent.create("Note B")
        result = notes_intent.get_all()
        assert result.was_intent_successful
        texts = {n.text for n in result.data}
        assert texts == {"Note A", "Note B"}

    def test_delete(self, notes_intent):
        created = notes_intent.create("To be deleted")
        note_id = created.data.id
        del_result = notes_intent.delete(note_id)
        assert del_result.was_intent_successful
        remaining = notes_intent.get_all()
        assert all(n.id != note_id for n in remaining.data)


@pytest.fixture
def fake():
    return faker.Faker()


class TestInvoiceNotesRendering:
    """Custom notes appear in rendered invoice HTML."""

    def test_custom_notes_in_html(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)
        invoice.notes = "Custom closing note for this client."

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            only_final=False,
        )

        assert "Custom closing note for this client." in html

    def test_default_closing_without_notes(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)
        invoice.notes = None

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            only_final=False,
        )

        assert "Custom closing note" not in html

    def test_notes_override_default_closing(self, fake):
        """When notes is set, the default 'Thank you' text must not appear."""
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)
        invoice.notes = "See you next quarter!"

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            only_final=False,
        )

        assert "See you next quarter!" in html
        assert "Thank you" not in html


class TestTaxCategoryPropagation:
    """Invoice items snapshot the contract's tax category at creation."""

    def _outside_scope_project(self, tag: str) -> Project:
        project = _build_fixed_price_project(Decimal("5000"), tag=tag)
        project.contract.VAT_rate = Decimal("0")
        project.contract.VAT_category = TaxCategory.outside_scope
        project.contract.validate_vat()
        return project

    def test_fixed_price_invoice_inherits_contract_category(self):
        project = self._outside_scope_project("#FPOutside")
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="FP-O-001",
            date=datetime.date(2022, 2, 1),
        )
        assert all(item.VAT_category is TaxCategory.outside_scope for item in invoice.items)
        assert invoice.is_outside_scope is True
        assert invoice.total == Decimal("5000")  # no VAT added

    def test_fixed_price_standard_contract_stays_standard(self):
        project = _build_fixed_price_project(Decimal("4500"), tag="#FPStd")
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="FP-S-001",
            date=datetime.date(2022, 2, 1),
        )
        assert all(item.VAT_category is TaxCategory.standard for item in invoice.items)
        assert invoice.is_outside_scope is False
        assert invoice.total == Decimal("5355.00")


class TestInvoicePaymentQR:
    """The SEPA payment (EPC/Girocode) QR code appears on invoices exactly when eligible."""

    VALID_IBAN = "DE89370400440532013000"

    def test_qr_appears_when_eligible(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(name=user.name, IBAN=self.VALID_IBAN, BIC="COBADEFFXXX")
        invoice = demo.create_fake_invoice(fake)

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            only_final=False,
            include_qr_code=True,
        )

        assert "payment-qr" in html
        assert "data:image/svg+xml" in html

    def test_qr_absent_when_toggle_off(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(name=user.name, IBAN=self.VALID_IBAN, BIC="COBADEFFXXX")
        invoice = demo.create_fake_invoice(fake)

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            only_final=False,
            include_qr_code=False,
        )

        assert "payment-qr" not in html

    def test_qr_absent_without_bank_account(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            only_final=False,
            include_qr_code=True,
        )

        assert "payment-qr" not in html

    def test_qr_absent_for_non_eur_invoice(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(name=user.name, IBAN=self.VALID_IBAN, BIC="COBADEFFXXX")
        contract = demo.create_fake_contract(fake)
        contract.currency = "USD"
        project = demo.create_fake_project(fake, contract=contract)
        invoice = demo.create_fake_invoice(fake, project=project, user=user)

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            only_final=False,
            include_qr_code=True,
        )

        assert "payment-qr" not in html


class TestGeneratePaymentQR:
    """Direct tests of rendering.generate_payment_qr(), independent of full HTML rendering."""

    VALID_IBAN = "DE89370400440532013000"

    def test_returns_none_without_bank_account(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)
        assert rendering.generate_payment_qr(user, invoice) is None

    def test_returns_none_for_non_eur_currency(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(name=user.name, IBAN=self.VALID_IBAN, BIC="COBADEFFXXX")
        contract = demo.create_fake_contract(fake)
        contract.currency = "USD"
        project = demo.create_fake_project(fake, contract=contract)
        invoice = demo.create_fake_invoice(fake, project=project, user=user)
        assert rendering.generate_payment_qr(user, invoice) is None

    def test_returns_svg_data_uri_when_eligible(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(name=user.name, IBAN=self.VALID_IBAN, BIC="COBADEFFXXX")
        invoice = demo.create_fake_invoice(fake)

        result = rendering.generate_payment_qr(user, invoice)

        assert result is not None
        assert result.startswith("data:image/svg+xml")
