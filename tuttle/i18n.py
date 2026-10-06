"""Translation of the documents clients receive.

Text is written in English where it is used — ``_("Due Date")`` in Python,
``{{ _("Due Date") }}`` in templates — and looked up in
``tuttle/locales/<lang>/LC_MESSAGES/messages.po``. A language is supported
when it has a catalog; ``just i18n`` refreshes the catalogs from the code.
"""

import io
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path

from babel import Locale
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from babel.support import NullTranslations, Translations

LOCALES_DIR = Path(__file__).parent / "locales"

SOURCE_LANGUAGE = "en"

# Region whose conventions format numbers, dates and money in a language.
# Languages not listed use the language's own defaults.
_FORMAT_LOCALES = {"en": "en_US", "de": "de_DE", "es": "es_ES"}

_current: ContextVar[str] = ContextVar("language", default=SOURCE_LANGUAGE)


def _discover_languages() -> dict[str, str]:
    codes = sorted(path.parent.parent.name for path in LOCALES_DIR.glob("*/LC_MESSAGES/messages.po"))
    return {code: Locale.parse(code).get_display_name(code).capitalize() for code in [SOURCE_LANGUAGE, *codes]}


#: Language code → the language's own name, e.g. ``{"de": "Deutsch"}``.
SUPPORTED: dict[str, str] = _discover_languages()


@lru_cache
def _translations(language: str) -> NullTranslations:
    po_path = LOCALES_DIR / language / "LC_MESSAGES" / "messages.po"
    if not po_path.exists():
        return NullTranslations()
    with po_path.open("rb") as po_file:
        catalog = read_po(po_file, locale=language)
    mo_file = io.BytesIO()
    write_mo(mo_file, catalog)
    mo_file.seek(0)
    return Translations(mo_file)


@contextmanager
def use_language(language: str):
    """Translate and format everything inside the block in ``language``."""
    token = _current.set(language or SOURCE_LANGUAGE)
    try:
        yield
    finally:
        _current.reset(token)


def current_language() -> str:
    return _current.get()


def babel_locale() -> str:
    """Babel locale for formatting numbers, dates and money in the current language."""
    language = _current.get()
    return _FORMAT_LOCALES.get(language, language)


def _fill(text: str, source: str, values: dict) -> str:
    if not values:
        return text
    try:
        return text.format(**values)
    except (KeyError, IndexError, ValueError):
        # A translation with a broken placeholder must not break the document.
        return source.format(**values)


def _(message: str, **values) -> str:
    """``message`` in the current language, with ``{placeholders}`` filled from ``values``."""
    return _fill(_translations(_current.get()).gettext(message), message, values)


def ngettext(singular: str, plural: str, n, **values) -> str:
    """The form of ``singular``/``plural`` that matches the quantity ``n`` in the current language."""
    count = float(n)
    # gettext plural rules are defined on whole numbers. A fraction (1.5 hours)
    # takes the form of 2: the plural in English, German and Spanish.
    count = int(count) if count.is_integer() else 2
    source = singular if count == 1 else plural
    return _fill(_translations(_current.get()).ngettext(singular, plural, count), source, values)
