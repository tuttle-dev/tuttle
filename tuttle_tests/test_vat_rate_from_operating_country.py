"""A contract's VAT rate comes from the user, preset from their operating country.

Contracts used to default to 19%, Germany's rate, for everyone, and the
contract form saved an emptied VAT field as 0%. Now the rate has no default:
every write path states it, and the form presets the operating country's
standard rate where Tuttle knows it.
"""

from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.contracts.intent import ContractsIntent
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.imports.intent import _validate_import_data
from tuttle.model import Contract, TaxCategory, User


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _payload(**overrides) -> dict:
    """A new contract as the contract form sends it."""
    payload = {
        "title": "Boiler Service",
        "type": "time_based",
        "rate": 95,
        "currency": "EUR",
        "unit": "hour",
        "billing_cycle": "monthly",
        "volume": 40,
        "units_per_workday": 8,
        "VAT_rate": 0.21,
        "VAT_category": "S",
        "start_date": "2026-01-01",
    }
    payload.update(overrides)
    return payload


class TestNoDefaultRate:
    def test_the_model_has_no_default_rate(self):
        assert Contract.model_fields["VAT_rate"].is_required()

    def test_a_contract_without_a_rate_is_not_saved(self, in_memory_db):
        result = ContractsIntent().save_from_dict(_payload(VAT_rate=None))
        assert not result.was_intent_successful
        assert result.error_msg == "VAT rate is required."
        with Session(in_memory_db) as session:
            assert session.exec(select(Contract)).all() == []

    def test_a_contract_with_a_rate_keeps_it(self, in_memory_db):
        assert ContractsIntent().save_from_dict(_payload()).was_intent_successful
        with Session(in_memory_db) as session:
            assert session.exec(select(Contract)).one().VAT_rate == Decimal("0.21")

    def test_outside_the_scope_of_vat_the_rate_is_zero(self, in_memory_db):
        result = ContractsIntent().save_from_dict(_payload(VAT_rate=0, VAT_category="O"))
        assert result.was_intent_successful, result.error_msg
        with Session(in_memory_db) as session:
            assert session.exec(select(Contract)).one().VAT_category is TaxCategory.outside_scope

    def test_an_imported_contract_without_a_rate_is_not_committed(self):
        contract = {"ref": "c1", "title": "Boiler Service", "currency": "EUR", "start_date": "2026-01-01"}
        errors = _validate_import_data({"contracts": [contract]})
        assert any("Boiler Service" in e and "vat rate" in e.lower() for e in errors)


class TestPresetFromOperatingCountry:
    def _default_for(self, engine, country: str):
        with Session(engine) as session:
            session.add(
                User(name="Harry Tuttle", subtitle="Heating Engineer", email="mail@tuttle.example", operating_country=country)
            )
            session.commit()
        result = ContractsIntent().get_default_vat_rate()
        assert result.was_intent_successful
        return result.data

    @pytest.mark.parametrize("country, rate", [("Germany", "0.19"), ("Spain", "0.21"), ("Sweden", "0.25")])
    def test_a_country_with_a_tax_model_presets_its_standard_rate(self, in_memory_db, country, rate):
        assert self._default_for(in_memory_db, country) == Decimal(rate)

    def test_a_country_without_a_tax_model_presets_nothing(self, in_memory_db):
        assert self._default_for(in_memory_db, "Austria") is None

    def test_no_operating_country_presets_nothing(self, in_memory_db):
        assert self._default_for(in_memory_db, "") is None

    def test_a_tax_model_without_a_standard_rate_presets_nothing(self, in_memory_db):
        """A 0% standard rate in the tax data means no VAT is modelled, not a rate to bill."""
        assert self._default_for(in_memory_db, "United States") is None
