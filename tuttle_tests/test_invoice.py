"""Tests for the invoice module."""

import datetime
from decimal import Decimal

from unittest.mock import patch, MagicMock
import faker
import pandas
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.app.core.intent_result import IntentResult

from tuttle import demo, invoicing, rendering, timetracking
from tuttle.model import (
    Address,
    BankAccount,
    Client,
    Contract,
    Invoice,
    InvoiceItem,
    InvoiceNote,
    Project,
)
from tuttle.time import Cycle, TimeUnit
from tuttle.calendar import get_month_start_end


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
            (period_start, period_end) = get_month_start_end(period)
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


class TestInvoicePaymentQR:
    """Tests for invoice payment QR code generation."""

    def test_no_qr_when_bank_account_missing(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = None
        invoice = demo.create_fake_invoice(fake)

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
        )
        assert "payment-qr-code" not in html

    def test_no_qr_when_iban_missing(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(name="Test Account", IBAN="", BIC="COBADEFFXXX")
        invoice = demo.create_fake_invoice(fake)

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
        )
        assert "payment-qr-code" not in html

    def test_no_qr_when_currency_not_eur(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(
            name="Test Account", IBAN="DE89370400440532013000", BIC="COBADEFFXXX"
        )
        invoice = demo.create_fake_invoice(fake)
        invoice.contract.currency = "USD"

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
        )
        assert "payment-qr-code" not in html

    def test_qr_generation_with_valid_details(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(
            name="Test Account Holder", IBAN="DE89370400440532013000", BIC="COBADEFFXXX"
        )
        invoice = demo.create_fake_invoice(fake)
        invoice.contract.currency = "EUR"
        invoice.number = "INV-2026-99"

        # Explicitly mock/set items so we have a predictable total amount
        invoice.items = [
            InvoiceItem(
                start_date=datetime.date.today(),
                quantity=2.5,
                unit="hour",
                unit_price=Decimal("100.00"),
                description="Test Item",
                VAT_rate=Decimal("0.19"),
            )
        ]

        # 2.5 * 100 = 250.00, VAT = 250.00 * 0.19 = 47.50, Total = 297.50
        assert invoice.total == Decimal("297.50")

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
        )

        assert "payment-qr-code" in html
        assert "<svg" in html

    def test_no_qr_when_show_payment_qr_false(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(
            name="Test Account Holder", IBAN="DE89370400440532013000", BIC="COBADEFFXXX"
        )
        invoice = demo.create_fake_invoice(fake)
        invoice.contract.currency = "EUR"

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            show_payment_qr=False,
        )
        assert "payment-qr-code" not in html

    def test_qr_when_show_payment_qr_true(self, fake):
        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(
            name="Test Account Holder", IBAN="DE89370400440532013000", BIC="COBADEFFXXX"
        )
        invoice = demo.create_fake_invoice(fake)
        invoice.contract.currency = "EUR"

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            show_payment_qr=True,
        )
        assert "payment-qr-code" in html

    def test_qr_when_db_setting_false(self, fake):

        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(
            name="Test Account Holder", IBAN="DE89370400440532013000", BIC="COBADEFFXXX"
        )
        project = demo.create_fake_project(fake)
        project.contract.currency = "EUR"

        intent = InvoicingIntent()

        with patch("tuttle.app.invoicing.intent.UserDataSource.get_user", return_value=user), \
             patch("tuttle.app.invoicing.intent.PreferencesIntent.get", return_value=IntentResult(
                 was_intent_successful=True,
                 data={"show_payment_qr": False}
             )), \
             patch("tuttle.app.invoicing.intent.PreferencesIntent.get_preferred_invoice_template", return_value=IntentResult(
                 was_intent_successful=True,
                 data="invoice-modern"
             )), \
             patch("tuttle.app.invoicing.intent.InvoicingDataSource.generate_invoice_number", return_value="INV-001"), \
             patch("tuttle.app.invoicing.intent.InvoicingDataSource.save_invoice"), \
             patch("tuttle.app.invoicing.intent.rendering.render_invoice") as mock_render:

            intent.create_invoice(
                invoice_date=datetime.date.today(),
                project=project,
                from_date=datetime.date.today(),
                to_date=datetime.date.today(),
                render=True,
                manual_quantity=1.0,
            )
            mock_render.assert_called_once()
            kwargs = mock_render.call_args.kwargs
            assert kwargs.get("show_payment_qr") is False

    def test_qr_when_db_setting_true(self, fake):

        user = demo.create_fake_user(fake)
        user.bank_account = BankAccount(
            name="Test Account Holder", IBAN="DE89370400440532013000", BIC="COBADEFFXXX"
        )
        project = demo.create_fake_project(fake)
        project.contract.currency = "EUR"

        intent = InvoicingIntent()

        with patch("tuttle.app.invoicing.intent.UserDataSource.get_user", return_value=user), \
             patch("tuttle.app.invoicing.intent.PreferencesIntent.get", return_value=IntentResult(
                 was_intent_successful=True,
                 data={"show_payment_qr": True}
             )), \
             patch("tuttle.app.invoicing.intent.PreferencesIntent.get_preferred_invoice_template", return_value=IntentResult(
                 was_intent_successful=True,
                 data="invoice-modern"
             )), \
             patch("tuttle.app.invoicing.intent.InvoicingDataSource.generate_invoice_number", return_value="INV-001"), \
             patch("tuttle.app.invoicing.intent.InvoicingDataSource.save_invoice"), \
             patch("tuttle.app.invoicing.intent.rendering.render_invoice") as mock_render:

            intent.create_invoice(
                invoice_date=datetime.date.today(),
                project=project,
                from_date=datetime.date.today(),
                to_date=datetime.date.today(),
                render=True,
                manual_quantity=1.0,
            )
            mock_render.assert_called_once()
            kwargs = mock_render.call_args.kwargs
            assert kwargs.get("show_payment_qr") is True
