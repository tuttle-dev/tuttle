"""Data-driven tax calculation engine.

Tax systems are stored as JSON data packages in ``tuttle/tax_data/<country>/``.
Each file covers one year and contains all formula parameters (bracket
thresholds, polynomial coefficients, surcharge rates, VAT rates).

The engine loads the right year's data for any given date, so historical
invoices are taxed with the rules that were actually in force.

Adding a new year:  copy the JSON file, update the coefficients.
Adding a new country: create a new subdirectory with its own JSON files.
"""

from __future__ import annotations

import datetime
import json
from decimal import Decimal
from pathlib import Path
from typing import Optional

# ── Data package directory ────────────────────────────────────

_DATA_DIR = Path(__file__).parent / "tax_data"


# ── TaxParams: one loaded year for one country ───────────────


class TaxParams:
    """Tax parameters loaded from a single JSON data package."""

    def __init__(self, data: dict):
        self._data = data
        self.country: str = data["country"]
        self.aliases: list[str] = data.get("country_aliases", [])
        self.year: int = data["year"]
        self.formula_type: str = data["formula_type"]
        self.source: str = data.get("source", "")
        self.currency: str = data["currency"]

        it = data["income_tax"]
        self.basic_allowance = it["basic_allowance"]
        self.zones: list[dict] = it["zones"]

        soli = data.get("solidarity_surcharge", {})
        self.soli_rate: float = soli.get("rate", 0.0)

        vat = data.get("vat", {})
        self.vat_standard: float = vat.get("standard_rate", 0.0)
        self.vat_reduced: float = vat.get("reduced_rate", 0.0)


# ── Registry: country -> {year -> TaxParams} ─────────────────

# Maps canonical country name → {year → TaxParams}
_REGISTRY: dict[str, dict[int, TaxParams]] = {}
# Maps alias → canonical name
_ALIAS_MAP: dict[str, str] = {}


def _load_all() -> None:
    """Scan tax_data/ and populate the registry (once)."""
    if _REGISTRY:
        return
    if not _DATA_DIR.is_dir():
        return
    for country_dir in sorted(_DATA_DIR.iterdir()):
        if not country_dir.is_dir() or country_dir.name.startswith("_"):
            continue
        for json_path in sorted(country_dir.glob("*.json")):
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            params = TaxParams(data)
            canonical = params.country
            _REGISTRY.setdefault(canonical, {})[params.year] = params
            _ALIAS_MAP[canonical] = canonical
            for alias in params.aliases:
                _ALIAS_MAP[alias] = canonical


def _resolve_country(country: str) -> str:
    """Resolve a country name or alias to its canonical name."""
    _load_all()
    canonical = _ALIAS_MAP.get(country)
    if canonical is None:
        raise NotImplementedError(
            f"Tax system for '{country}' not yet implemented. "
            f"Supported: {', '.join(sorted(_ALIAS_MAP.keys()))}"
        )
    return canonical


def _get_params(country: str, year: int) -> TaxParams:
    """Get TaxParams for a country and year.

    Falls back to the closest available year if the exact year isn't found.
    """
    canonical = _resolve_country(country)
    years = _REGISTRY[canonical]
    if year in years:
        return years[year]
    # Fall back: nearest year (prefer most recent past year)
    available = sorted(years.keys())
    best = available[-1]  # latest available as default
    for y in available:
        if y <= year:
            best = y
    return years[best]


def supported_countries() -> list[str]:
    """Return list of country names that have tax data packages."""
    _load_all()
    return sorted(_REGISTRY.keys())


def has_tax_model(country: str) -> bool:
    """Check whether a country has a tax data package."""
    _load_all()
    return country in _ALIAS_MAP


# Comprehensive list of major countries for the operating-country dropdown.
# Countries with tax models appear here too; the UI distinguishes them via
# has_tax_model() / supported_countries().
ALL_COUNTRIES = sorted(
    [
        "Argentina",
        "Australia",
        "Austria",
        "Belgium",
        "Brazil",
        "Canada",
        "Chile",
        "China",
        "Colombia",
        "Croatia",
        "Czech Republic",
        "Denmark",
        "Egypt",
        "Estonia",
        "Finland",
        "France",
        "Germany",
        "Greece",
        "Hungary",
        "Iceland",
        "India",
        "Indonesia",
        "Ireland",
        "Israel",
        "Italy",
        "Japan",
        "Latvia",
        "Lithuania",
        "Luxembourg",
        "Malaysia",
        "Mexico",
        "Morocco",
        "Netherlands",
        "New Zealand",
        "Nigeria",
        "Norway",
        "Pakistan",
        "Peru",
        "Philippines",
        "Poland",
        "Portugal",
        "Romania",
        "Saudi Arabia",
        "Singapore",
        "Slovakia",
        "Slovenia",
        "South Africa",
        "South Korea",
        "Spain",
        "Sweden",
        "Switzerland",
        "Taiwan",
        "Thailand",
        "Turkey",
        "Ukraine",
        "United Arab Emirates",
        "United Kingdom",
        "United States",
        "Vietnam",
    ]
)


def all_operating_countries() -> list[str]:
    """All countries available for the operating-country dropdown."""
    return ALL_COUNTRIES


def available_years(country: str) -> list[int]:
    """Return sorted list of years available for a country."""
    canonical = _resolve_country(country)
    return sorted(_REGISTRY[canonical].keys())


# ── TaxSystem: computes taxes from TaxParams ──────────────────


class TaxSystem:
    """Tax calculation engine driven by a TaxParams data package.

    Instantiate via ``get_tax_system(country, year_or_date)``.
    """

    def __init__(self, params: TaxParams):
        self.params = params

    @property
    def country(self) -> str:
        return self.params.country

    @property
    def year(self) -> int:
        return self.params.year

    @property
    def currency(self) -> str:
        """ISO 4217 currency code for this tax system (e.g. "EUR", "USD")."""
        return self.params.currency

    @property
    def bracket_info(self) -> list[dict]:
        """Zone data for UI visualization."""
        return self.params.zones

    # ── Income tax ────────────────────────────────────────────

    def income_tax(self, taxable_income: Decimal) -> Decimal:
        """Compute income tax using the formula type from the data package."""
        if self.params.formula_type == "german_progressive":
            return self._german_progressive(float(taxable_income))
        elif self.params.formula_type == "marginal_brackets":
            return self._marginal_brackets(float(taxable_income))
        elif self.params.formula_type == "flat_rate":
            return self._flat_rate(float(taxable_income))
        raise NotImplementedError(f"Unknown formula type: {self.params.formula_type}")

    def _german_progressive(self, ti: float) -> Decimal:
        """§32a EStG formula with zone parameters from data."""
        for zone in self.params.zones:
            up_to = zone["up_to"]
            if up_to is not None and ti > up_to:
                continue
            ztype = zone["type"]
            if ztype == "zero":
                return Decimal(0)
            elif ztype == "quadratic":
                ref = zone["reference_offset"]
                div = zone["divisor"]
                a = zone["a"]
                b = zone["b"]
                c = zone.get("c", 0)
                y = (ti - ref) / div
                tax = (a * y + b) * y + c
                return Decimal(str(round(tax)))
            elif ztype == "linear":
                rate = zone["rate"]
                offset = zone["offset"]
                tax = rate * ti + offset
                return Decimal(str(round(tax)))
        return Decimal(0)

    def _marginal_brackets(self, ti: float) -> Decimal:
        """Standard marginal bracket formula (used by most countries).

        Each zone defines a marginal rate applied only to the income
        within that bracket. The personal allowance is handled as a
        zone with rate 0.
        """
        ti = max(ti - self.params.basic_allowance, 0)
        total_tax = 0.0
        prev_limit = 0.0
        for zone in self.params.zones:
            rate = zone["rate"]
            up_to = zone["up_to"]
            if up_to is None:
                # Top bracket — all remaining income
                taxable_in_zone = max(ti - prev_limit, 0)
            else:
                bracket_width = up_to - prev_limit
                taxable_in_zone = min(max(ti - prev_limit, 0), bracket_width)
            total_tax += taxable_in_zone * rate
            if up_to is not None and ti <= up_to:
                break
            prev_limit = up_to if up_to is not None else prev_limit
        return Decimal(str(round(total_tax)))

    def _flat_rate(self, ti: float) -> Decimal:
        """Flat-rate income tax (e.g. Estonia).

        A single rate applied to all income above the basic allowance.
        """
        taxable = max(ti - self.params.basic_allowance, 0)
        rate = self.params.zones[0]["rate"]
        return Decimal(str(round(taxable * rate)))

    # ── Solidarity surcharge ──────────────────────────────────

    def solidarity_surcharge(self, income_tax_amount: Decimal) -> Decimal:
        """Surcharge on income tax (e.g. 5.5% Solidaritätszuschlag)."""
        if income_tax_amount <= 0 or self.params.soli_rate == 0:
            return Decimal(0)
        surcharge = income_tax_amount * Decimal(str(self.params.soli_rate))
        return surcharge.quantize(Decimal("0.01"))

    def total_tax(self, taxable_income: Decimal) -> Decimal:
        """Income tax + all surcharges."""
        it = self.income_tax(taxable_income)
        soli = self.solidarity_surcharge(it)
        return it + soli

    # ── VAT ───────────────────────────────────────────────────

    def vat_rate_standard(self) -> Decimal:
        return Decimal(str(self.params.vat_standard))

    def vat_rate_reduced(self) -> Decimal:
        return Decimal(str(self.params.vat_reduced))


# ── Public factory ────────────────────────────────────────────


def get_tax_system(
    country: str,
    date: Optional[datetime.date] = None,
) -> TaxSystem:
    """Get a TaxSystem for the given country and date.

    Args:
        country: Country name or alias (e.g. "Germany", "Deutschland").
        date: Date determining which year's tax rules apply.
              Defaults to today.

    Raises:
        NotImplementedError: If the country has no data packages.
    """
    if date is None:
        date = datetime.date.today()
    params = _get_params(country, date.year)
    return TaxSystem(params)


# ── Backward-compatible API ───────────────────────────────────


def income_tax(taxable_income: Decimal, country: str) -> Decimal:
    """Compute income tax for a given country (current year). Legacy wrapper."""
    system = get_tax_system(country)
    return system.income_tax(taxable_income)


def income_tax_germany(taxable_income: Decimal) -> Decimal:
    """Income tax using the current German tariff. Legacy wrapper."""
    return get_tax_system("Germany").income_tax(taxable_income)
