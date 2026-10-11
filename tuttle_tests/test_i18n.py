"""Tests for the translation of client-facing documents."""

import datetime
import re
from decimal import Decimal
from functools import cache
from html.parser import HTMLParser
from pathlib import Path

import faker
import jinja2
import pytest
from babel.messages.extract import extract_from_dir
from babel.messages.frontend import parse_mapping_cfg
from babel.messages.pofile import read_po

from tuttle import demo, i18n, invoicing, rendering
from tuttle.i18n import _, ngettext, use_language
from tuttle.model import Client, ClientContact, Contact, Contract, Invoice, Project, User
from tuttle.time import Cycle, TimeUnit


class TestLookup:
    def test_each_catalog_is_listed_by_its_own_name(self):
        assert i18n.SUPPORTED["en"] == "English"
        assert i18n.SUPPORTED["de"] == "Deutsch"
        assert i18n.SUPPORTED["es"] == "Español"

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


REPO = Path(__file__).parent.parent
TEMPLATES = REPO / "templates"

#: Every template a client document is rendered from, and the macros they share.
DOCUMENT_TEMPLATES = sorted(
    [
        *TEMPLATES.glob("invoice*/invoice.html"),
        *TEMPLATES.glob("_shared/*.html"),
        TEMPLATES / "timesheet-anvil" / "timesheet.html",
    ]
)
INVOICE_STYLES = sorted(path.parent.name for path in TEMPLATES.glob("invoice*/invoice.html"))
TRANSLATED_LANGUAGES = [code for code in i18n.SUPPORTED if code != i18n.SOURCE_LANGUAGE]

#: Words that read the same in every language.
LANGUAGE_NEUTRAL = {"IBAN", "BIC"}


class _VisibleText(HTMLParser):
    """The text a reader sees on an HTML page: no tags, comments, styles or scripts."""

    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def _literal_words(template: Path) -> list[str]:
    """Words ``template`` writes out as they are instead of through ``_()``."""
    # Keep the template's own text; every {{ … }} and {% … %} becomes a space.
    tokens = jinja2.Environment().lex(template.read_text(encoding="utf-8"))
    page = _VisibleText()
    page.feed("".join(value if kind == "data" else " " for _lineno, kind, value in tokens))
    return [word for word in re.findall(r"[A-Za-z]{2,}", " ".join(page.text)) if word not in LANGUAGE_NEUTRAL]


@cache
def _messages_in_code() -> frozenset[str]:
    """The messages ``just i18n`` extracts, plurals by their singular as in the catalogs."""
    with (REPO / "babel.cfg").open() as config:
        method_map, options_map = parse_mapping_cfg(config)
    found = extract_from_dir(
        REPO,
        method_map,
        options_map,
        directory_filter=lambda path: not Path(path).name.startswith(".") and Path(path).name != "node_modules",
    )
    return frozenset(
        message[0] if isinstance(message, tuple) else message for _file, _lineno, message, _notes, _context in found
    )


def _is_translated(message) -> bool:
    forms = message.string if isinstance(message.string, tuple) else (message.string,)
    return not message.fuzzy and all(forms)


class TestEveryDocument:
    """Every client document can be produced in every supported language."""

    @pytest.mark.parametrize("template", DOCUMENT_TEMPLATES, ids=lambda path: str(path.relative_to(TEMPLATES)))
    def test_template_writes_its_text_through_gettext(self, template):
        assert _literal_words(template) == []

    @pytest.mark.parametrize("language", TRANSLATED_LANGUAGES)
    def test_catalog_translates_every_message(self, language):
        with (i18n.LOCALES_DIR / language / "LC_MESSAGES" / "messages.po").open("rb") as po_file:
            catalog = read_po(po_file, locale=language)
        untranslated = sorted(
            msgid for msgid in _messages_in_code() if msgid not in catalog or not _is_translated(catalog[msgid])
        )
        assert untranslated == [], "run `just i18n` and translate these"

    @pytest.mark.parametrize("language", TRANSLATED_LANGUAGES)
    @pytest.mark.parametrize("style", INVOICE_STYLES)
    def test_invoice_is_marked_with_its_language(self, style, language):
        fake = faker.Faker()
        html = rendering.render_invoice(
            user=demo.create_fake_user(fake),
            invoice=demo.create_fake_invoice(fake, render=False),
            out_dir=None,
            document_format="html",
            template_name=style,
            language=language,
        )
        assert f'lang="{language}"' in html


class TestCzech:
    def test_is_listed_by_its_own_name(self):
        assert i18n.SUPPORTED["cs"] == "Čeština"

    @pytest.mark.parametrize("days,expected", [(1, "Splatnost 1 den"), (3, "Splatnost 3 dny"), (14, "Splatnost 14 dní")])
    def test_uses_all_three_plural_forms(self, days, expected):
        with use_language("cs"):
            assert ngettext("Net {days} day", "Net {days} days", days, days=days) == expected

    def test_invoice_is_written_in_czech(self):
        fake = faker.Faker()
        html = rendering.render_invoice(
            user=demo.create_fake_user(fake),
            invoice=demo.create_fake_invoice(fake),
            out_dir=None,
            document_format="html",
            language="cs",
        )
        assert '<html lang="cs">' in html
        assert "Faktura č." in html
        assert "Celkem k úhradě" in html
