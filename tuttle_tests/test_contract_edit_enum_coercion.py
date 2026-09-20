"""Editing a contract must coerce enum fields the same way creating one does.

The UI sends enum values as their names ("fixed_price", "day", ...). On create
they pass through ``model_validate`` and become enum members; on edit they were
set on the tracked entity verbatim, so ``validate_pricing`` compared a string
against ``ContractType.fixed_price`` and rejected every fixed-price edit with
"A time-based contract needs a rate."
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.contracts.intent import ContractsIntent
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.model import Contract
from tuttle.time import ContractType, Cycle, TimeUnit


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _fixed_price_payload(**overrides) -> dict:
    payload = {
        "title": "Boiler Replacement",
        "type": "fixed_price",
        "fixed_price": 12000,
        "rate": None,
        "currency": "EUR",
        "unit": "hour",
        "billing_cycle": "monthly",
        "units_per_workday": 8,
        "VAT_rate": 0.19,
        "start_date": "2026-01-01",
        "term_of_payment": 31,
    }
    payload.update(overrides)
    return payload


def _saved_contract(engine) -> Contract:
    with Session(engine) as session:
        return session.exec(select(Contract)).one()


def test_editing_a_fixed_price_contract_is_accepted(in_memory_db):
    intent = ContractsIntent()
    assert intent.save_from_dict(_fixed_price_payload()).was_intent_successful
    contract_id = _saved_contract(in_memory_db).id

    result = intent.save_from_dict(_fixed_price_payload(id=contract_id, fixed_price=15000))

    assert result.was_intent_successful, result.error_msg
    saved = _saved_contract(in_memory_db)
    assert saved.type is ContractType.fixed_price
    assert saved.fixed_price == 15000
    assert saved.rate is None


def test_switching_a_time_based_contract_to_fixed_price_is_accepted(in_memory_db):
    intent = ContractsIntent()
    created = intent.save_from_dict(_fixed_price_payload(type="time_based", rate=95, fixed_price=None))
    assert created.was_intent_successful, created.error_msg
    contract_id = _saved_contract(in_memory_db).id

    result = intent.save_from_dict(_fixed_price_payload(id=contract_id))

    assert result.was_intent_successful, result.error_msg
    saved = _saved_contract(in_memory_db)
    assert saved.type is ContractType.fixed_price
    assert saved.rate is None


def test_edit_leaves_enum_members_on_the_entity(in_memory_db):
    """Not just ``type``: every enum field is a member after an edit, so code
    that compares against members before flush behaves the same as on create."""
    intent = ContractsIntent()
    intent.save_from_dict(_fixed_price_payload())
    contract_id = _saved_contract(in_memory_db).id

    result = intent.save_from_dict(_fixed_price_payload(id=contract_id, unit="day", billing_cycle="quarterly"))

    assert result.was_intent_successful, result.error_msg
    assert result.data.type is ContractType.fixed_price
    assert result.data.unit is TimeUnit.day
    assert result.data.billing_cycle is Cycle.quarterly
