"""Checks on the tax data packages in tuttle/tax_data/."""

import datetime
import json

import pytest

from tuttle import tax
from tuttle.tax import ALL_COUNTRIES, supported_countries

#: The ten largest EU economies by nominal GDP.
LARGEST_EU_ECONOMIES = [
    "Germany",
    "France",
    "Italy",
    "Spain",
    "Netherlands",
    "Poland",
    "Belgium",
    "Sweden",
    "Ireland",
    "Austria",
]

PACKAGES = sorted(p for p in tax._DATA_DIR.glob("*/*.json"))


def test_the_largest_eu_economies_have_a_tax_model():
    assert set(LARGEST_EU_ECONOMIES) <= set(supported_countries())


@pytest.mark.parametrize("country", supported_countries())
def test_every_country_has_rules_for_the_current_year(country):
    """Fails from 1 January until the new year's tax data is added: without it the app shows no tax figures."""
    year = datetime.date.today().year
    folder = country.lower().replace(" ", "_")
    assert year in tax.available_years(country), f"No {year} tax rules for {country}: add tuttle/tax_data/{folder}/{year}.json"


@pytest.mark.parametrize("country", supported_countries())
def test_every_country_has_rules_for_2026_and_2027(country):
    assert {2026, 2027} <= set(tax.available_years(country))


@pytest.mark.parametrize("country", supported_countries())
def test_every_country_with_rules_can_be_chosen(country):
    assert country in ALL_COUNTRIES


def test_no_alias_names_two_countries():
    seen = {}
    for path in PACKAGES:
        data = json.loads(path.read_text(encoding="utf-8"))
        for name in [data["country"], *data.get("country_aliases", [])]:
            assert seen.setdefault(name, data["country"]) == data["country"], name


@pytest.mark.parametrize("path", PACKAGES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_package_is_well_formed(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["year"] == int(path.stem)
    assert path.parent.name == data["country"].lower().replace(" ", "_")
    assert data["formula_type"] in {"german_progressive", "marginal_brackets", "flat_rate"}
    assert len(data["currency"]) == 3 and data["currency"].isupper()
    assert data["source"]

    zones = data["income_tax"]["zones"]
    *limits, last = [z["up_to"] for z in zones]
    assert last is None
    assert all(a < b for a, b in zip(limits, limits[1:])), "zone limits must increase"
    for zone in zones:
        assert 0 <= zone.get("rate", 0) < 1

    vat = data["vat"]
    assert 0 <= vat["reduced_rate"] <= vat["standard_rate"] < 1
