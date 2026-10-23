"""Formatting utilities."""

from babel.numbers import format_currency as _babel_format_currency
from babel.numbers import format_decimal as _babel_format_decimal


def fmt_currency(value, currency: str = "EUR", locale: str = "en_US") -> str:
    """Format a numeric value as a currency string using babel.

    Args:
        value: Decimal, float, or int to format. None returns "---".
        currency: ISO 4217 code (e.g. "EUR", "USD", "SEK").
        locale: Babel locale for number formatting.
    """
    if value is None:
        return "—"
    return _babel_format_currency(float(value), currency, locale=locale)


def fmt_quantity(value, locale: str = "en_US") -> str:
    """Format an invoice quantity with up to two decimals: "8", "0.5", "1.33".

    Pass a quantity rounded with ``model.round_quantity``: Babel itself would
    round any further decimals half to even.
    """
    return _babel_format_decimal(value, format="#,##0.##", locale=locale)
