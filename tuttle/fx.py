"""Currency conversion for aggregates.

Invoices stay in their contract currency; only sums across invoices convert.
The rate is the ECB monthly average for the month of the invoice date — the
rate German tax law prescribes (§ 16 Abs. 6 UStG) and a value that never
changes once the month is closed, so it needs no column and no migration.

Source: frankfurter.dev (ECB data, no API key). Closed months are cached in
``app_db`` so the app keeps working offline. A month that can be resolved
neither from cache nor from the network yields ``None`` — never zero.
"""

import datetime
import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal
from functools import lru_cache
from typing import Optional

from .app_db import AppDatabase
from .tax import get_tax_system

logger = logging.getLogger(__name__)

# The ECB reference set as published on 2026-07-14; used when the API is
# unreachable. supported_currencies() prefers the live list.
SUPPORTED_CURRENCIES = (
    "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD",
    "HUF", "IDR", "ILS", "INR", "ISK", "JPY", "KRW", "MXN", "MYR", "NOK",
    "NZD", "PHP", "PLN", "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR",
)

_API = "https://api.frankfurter.dev/v1"
_TIMEOUT = 5.0


# -- Settings -----------------------------------------------------------------


@lru_cache(maxsize=1)
def supported_currencies() -> tuple[str, ...]:
    """Currencies the rate source publishes rates for."""
    request = urllib.request.Request(
        f"{_API}/currencies", headers={"User-Agent": "tuttle"}
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:
            return tuple(sorted(json.load(resp)))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        logger.warning("Currency list unavailable (%s); using the built-in set.", e)
        return SUPPORTED_CURRENCIES


def primary_currency(country: str = "Germany") -> str:
    """The currency all aggregates are expressed in.

    Defaults to the currency of the operating country's tax system, which is
    why preselection by country needs no country→currency table.
    """
    setting = AppDatabase().get_setting("currency.primary")
    if setting:
        return setting
    try:
        return get_tax_system(country).currency
    except NotImplementedError:
        return "EUR"


def validate_currency_code(code: str) -> str:
    """Normalise an ISO 4217 code and reject one we cannot convert.

    Aggregates convert foreign-currency amounts at the ECB monthly average, so
    a code the rate source does not publish would never convert and would drop
    out of every total. Rejecting it on write beats discovering it in a sum.
    """
    normalized = (code or "").strip().upper()
    supported = supported_currencies()
    if normalized not in supported:
        raise ValueError(
            f"Unsupported currency {code!r}. Supported: {', '.join(supported)}."
        )
    return normalized


def fx_haircut() -> Decimal:
    """Bank/exchange spread in percent, deducted from the salary estimate only.

    Never reduces taxable revenue — the taxable amount is the ECB-converted one.
    """
    raw = AppDatabase().get_setting("currency.fx_haircut")
    try:
        return Decimal(raw) if raw else Decimal("1.0")
    except (ArithmeticError, ValueError):
        return Decimal("1.0")


# -- Rates --------------------------------------------------------------------


def _month_range(month: datetime.date) -> tuple[datetime.date, datetime.date]:
    start = month.replace(day=1)
    next_month = (start + datetime.timedelta(days=32)).replace(day=1)
    return start, next_month - datetime.timedelta(days=1)


def _fetch_monthly_average(base: str, quote: str, month: datetime.date) -> Decimal:
    """Average the ECB daily rates published for *month*."""
    start, end = _month_range(month)
    url = f"{_API}/{start}..{end}?base={base}&symbols={quote}"
    # The API rejects urllib's default User-Agent with 403.
    request = urllib.request.Request(url, headers={"User-Agent": "tuttle"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:
        payload = json.load(resp)
    # When the range starts on a non-trading day the API backfills the previous
    # business day, which can belong to the previous month — drop those.
    daily = [
        Decimal(str(day[quote]))
        for iso, day in payload["rates"].items()
        if quote in day and iso.startswith(f"{start:%Y-%m}")
    ]
    if not daily:
        raise ValueError(f"no {base}/{quote} rates published for {start:%Y-%m}")
    return sum(daily) / len(daily)


# ponytail: a failed lookup stays cached for the session; restart (or call
# clear_cache) after coming back online. Retry-on-reconnect if that annoys anyone.
@lru_cache(maxsize=256)
def _rate(base: str, quote: str, month_key: str) -> Optional[Decimal]:
    month = datetime.date.fromisoformat(f"{month_key}-01")
    db = AppDatabase()
    cache_key = f"fx.rate.{base}.{quote}.{month_key}"

    cached = db.get_setting(cache_key)
    if cached:
        return Decimal(cached)

    try:
        avg = _fetch_monthly_average(base, quote, month)
    except (urllib.error.URLError, OSError, ValueError, KeyError, TimeoutError) as e:
        logger.warning(
            "No exchange rate for %s/%s in %s (%s); amounts in %s are left "
            "unconverted rather than counted as zero.",
            base,
            quote,
            month_key,
            e,
            base,
        )
        return None

    # A closed month's average is final; the running month's is not, so only
    # the closed one is worth persisting.
    if _month_range(month)[1] < datetime.date.today():
        db.set_setting(cache_key, str(avg))
    return avg


def rate(base: str, quote: str, month: datetime.date) -> Optional[Decimal]:
    """ECB monthly average: how many *quote* units one *base* unit buys.

    Returns ``None`` when the rate cannot be resolved (no cache, no network).
    """
    if base == quote:
        return Decimal(1)
    return _rate(base, quote, f"{month:%Y-%m}")


def convert(
    amount: Decimal, base: str, quote: str, on: datetime.date
) -> Optional[Decimal]:
    """Convert *amount* from *base* to *quote* at the rate for the month of *on*."""
    if base == quote:
        return amount
    r = rate(base, quote, on)
    if r is None:
        return None
    return (Decimal(amount) * r).quantize(Decimal("0.01"))


def clear_cache() -> None:
    """Drop the in-process caches (tests, and after a settings change)."""
    _rate.cache_clear()
    supported_currencies.cache_clear()
