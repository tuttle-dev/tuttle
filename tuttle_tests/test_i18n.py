"""Tests for the translation of client-facing documents."""

import datetime
from decimal import Decimal

import faker
import pytest

from tuttle import demo, i18n, invoicing, rendering
from tuttle.i18n import _, ngettext, use_language
from tuttle.model import Client, ClientContact, Contact, Contract, Invoice, Project, User
from tuttle.time import Cycle, TimeUnit


class TestLookup:
    def test_each_catalog_is_listed_by_its_own_name(self):
        assert i18n.SUPPORTED["en"] == "English"
        assert i18n.SUPPORTED["de"] == "Deutsch"
        assert i18n.SUPPORTED["es"] == "Español"
        assert i18n.SUPPORTED["it"] == "Italiano"

    def test_translates_only_inside_use_language(self):
        with use_language("de"):
            assert _("Due Date") == "Fälligkeitsdatum"
        assert _("Due Date") == "Due Date"

    def test_missing_translation_falls_back_to_english(self):
        with use_language("de"):
            assert _("A sentence nobody has translated") == "A sentence nobody has translated"
        with use_language("xx"):
            assert _("Due Date") == "Due Date"

    def test_placeholders_are_filled(self):
        with use_language("de"):
            assert _("{n}. Payment Reminder", n=2) == "2. Mahnung"

    @pytest.mark.parametrize("quantity,expected", [(1, "Stunde"), (1.0, "Stunde"), (2, "Stunden"), (1.5, "Stunden")])
    def test_plural_form_matches_quantity(self, quantity, expected):
        with use_language("de"):
            assert ngettext("hour", "hours", quantity) == expected

    @pytest.mark.parametrize(
        "unit,quantity,expected",
        [
            ("hours", 1, "Stunde"),
            ("hours", 3, "Stunden"),
            ("day", 2, "Tage"),
            ("piece", 2, "Stück"),
            ("flat", 1, "pauschal"),
            ("fixed price", 1, "pauschal"),
            ("m²", 2, "m²"),
        ],
    )
    def test_invoice_units_are_translated(self, unit, quantity, expected):
        with use_language("de"):
            assert rendering.unit_label(unit, quantity) == expected

    def test_broken_placeholder_in_a_translation_falls_back_to_english(self, tmp_path, monkeypatch):
        catalog = tmp_path / "xx" / "LC_MESSAGES" / "messages.po"
        catalog.parent.mkdir(parents=True)
        catalog.write_text('msgid ""\nmsgstr ""\n\nmsgid "Invoice {number}"\nmsgstr "Faktura {numero}"\n', encoding="utf-8")
        monkeypatch.setattr(i18n, "LOCALES_DIR", tmp_path)
        i18n._translations.cache_clear()
        try:
            with use_language("xx"):
                assert _("Invoice {number}", number="7") == "Invoice 7"
        finally:
            i18n._translations.cache_clear()


def _invoice_to_jill(reminder_level: int = 0) -> Invoice:
    contact = Contact(first_name="Jill", last_name="Layton", email="jill@example.com")
    client = Client(name="Central Services")
    client.client_contacts.append(ClientContact(client=client, contact=contact, role="invoicing"))
    contract = Contract(
        title="Retainer",
        client=client,
        rate=Decimal("100"),
        currency="EUR",
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )
    return Invoice(
        number="2026-07",
        date=datetime.date(2026, 7, 29),
        contract=contract,
        project=Project(title="Ducts"),
        document_type="reminder" if reminder_level else "invoice",
        reminder_level=reminder_level,
    )


class TestEmail:
    def test_is_written_in_the_document_language(self):
        with use_language("de"):
            email = invoicing.generate_invoice_email(_invoice_to_jill(), User(name="Harry Tuttle"))
        assert email["subject"] == "Rechnung 2026-07"
        assert email["body"].startswith("Guten Tag Jill Layton,")
        assert "Rechnung für Ducts" in email["body"]
        assert email["body"].endswith("Harry Tuttle")

    @pytest.mark.parametrize(
        "level,phrase", [(1, "This is a reminder"), (2, "2nd reminder"), (3, "3rd reminder"), (4, "3rd reminder")]
    )
    def test_reminder_names_its_level(self, level, phrase):
        email = invoicing.generate_invoice_email(_invoice_to_jill(level), User(name="Harry Tuttle"))
        assert email["subject"] == "Payment Reminder: Invoice 2026-07"
        assert phrase in email["body"]


class TestTimesheet:
    def test_is_written_in_the_document_language(self):
        fake = faker.Faker()
        timesheet = demo.create_fake_timesheet(fake)
        html = rendering.render_timesheet(user=demo.create_fake_user(fake), timesheet=timesheet, out_dir=None, language="de")
        assert '<html class="no-js" lang="de">' in html
        assert "Stundennachweis" in html
        assert "Auftraggeber" in html
        assert ">Client<" not in html
