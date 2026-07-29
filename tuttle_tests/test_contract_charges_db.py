"""Database-backed behaviour of additional contract charges.

Covers the two rules that cannot be checked without persistence: a one-time
charge is billed exactly once over the life of a contract, and the charge
list survives an edit of the contract that owns it.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.contracts.intent import ContractsIntent
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.model import Contract, ContractCharge, Invoice, InvoiceItem, Project
from tuttle.time import ChargeBasis


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _contract_payload(**overrides) -> dict:
    payload = {
        "title": "On-Site Retrofit",
        "type": "time_based",
        "rate": 640,
        "currency": "EUR",
        "unit": "day",
        "units_per_workday": 8,
        "VAT_rate": 0.19,
        "start_date": "2026-01-01",
        "term_of_payment": 14,
    }
    payload.update(overrides)
    return payload


def _saved_contract(engine) -> Contract:
    with Session(engine) as session:
        return session.exec(select(Contract)).one()


class TestChargePersistence:
    """The charges list round-trips through the contract save path."""

    def test_charges_are_saved_with_the_contract(self, in_memory_db):
        result = ContractsIntent().save_from_dict(
            _contract_payload(
                charges=[
                    {"description": "Daily allowance", "amount": 85, "basis": "per_unit"},
                    {"description": "Setup fee", "amount": 450, "basis": "once"},
                ]
            )
        )
        assert result.was_intent_successful, result.error_msg

        contract = _saved_contract(in_memory_db)
        assert [(c.description, c.amount, c.basis) for c in contract.charges] == [
            ("Daily allowance", Decimal("85.00"), ChargeBasis.per_unit),
            ("Setup fee", Decimal("450.00"), ChargeBasis.once),
        ]

    def test_editing_keeps_untouched_charges_identical(self, in_memory_db):
        """A charge keeps its id across an edit, so its billing history holds."""
        intent = ContractsIntent()
        intent.save_from_dict(
            _contract_payload(charges=[{"description": "Daily allowance", "amount": 85, "basis": "per_unit"}])
        )
        contract = _saved_contract(in_memory_db)
        original_id = contract.charges[0].id

        result = intent.save_from_dict(
            _contract_payload(
                id=contract.id,
                charges=[
                    {"id": original_id, "description": "Daily allowance", "amount": 95, "basis": "per_unit"},
                    {"description": "Handling", "amount": 25, "basis": "per_invoice"},
                ],
            )
        )
        assert result.was_intent_successful, result.error_msg

        contract = _saved_contract(in_memory_db)
        assert [c.id for c in contract.charges][0] == original_id
        assert contract.charges[0].amount == Decimal("95.00")
        assert len(contract.charges) == 2

    def test_removed_charges_are_deleted(self, in_memory_db):
        intent = ContractsIntent()
        intent.save_from_dict(
            _contract_payload(charges=[{"description": "Daily allowance", "amount": 85, "basis": "per_unit"}])
        )
        contract = _saved_contract(in_memory_db)

        intent.save_from_dict(_contract_payload(id=contract.id, charges=[]))

        with Session(in_memory_db) as session:
            assert session.exec(select(ContractCharge)).all() == []

    def test_a_payload_without_charges_leaves_them_alone(self, in_memory_db):
        """The document-import path omits the key and must not wipe charges."""
        intent = ContractsIntent()
        intent.save_from_dict(
            _contract_payload(charges=[{"description": "Daily allowance", "amount": 85, "basis": "per_unit"}])
        )
        contract = _saved_contract(in_memory_db)

        intent.save_from_dict(_contract_payload(id=contract.id, title="Renamed Retrofit"))

        contract = _saved_contract(in_memory_db)
        assert contract.title == "Renamed Retrofit"
        assert len(contract.charges) == 1

    def test_an_invalid_charge_is_rejected(self, in_memory_db):
        result = ContractsIntent().save_from_dict(
            _contract_payload(charges=[{"description": "Freebie", "amount": 0, "basis": "per_invoice"}])
        )
        assert not result.was_intent_successful
        assert "greater than zero" in result.error_msg


class TestOnceOnlyCharges:
    """A one-time charge drops out once it has actually been billed."""

    def _contract_with_setup_fee(self, engine) -> Contract:
        ContractsIntent().save_from_dict(
            _contract_payload(
                charges=[
                    {"description": "Daily allowance", "amount": 85, "basis": "per_unit"},
                    {"description": "Setup fee", "amount": 450, "basis": "once"},
                ]
            )
        )
        return _saved_contract(engine)

    def _bill(self, engine, contract: Contract, charge: ContractCharge, cancelled: bool = False) -> None:
        with Session(engine) as session:
            session.add(
                Invoice(
                    number=f"INV-{charge.id}-{int(cancelled)}",
                    date=datetime.date(2026, 2, 1),
                    contract_id=contract.id,
                    cancelled=cancelled,
                    items=[
                        InvoiceItem(
                            quantity=1,
                            unit="flat",
                            unit_price=charge.amount,
                            description=charge.description,
                            VAT_rate=Decimal("0.19"),
                            contract_charge_id=charge.id,
                        )
                    ],
                )
            )
            session.commit()

    def test_eligible_on_the_first_invoice(self, in_memory_db):
        contract = self._contract_with_setup_fee(in_memory_db)
        eligible = InvoicingIntent()._eligible_charges(contract)
        assert [c.description for c in eligible] == ["Daily allowance", "Setup fee"]

    def test_dropped_once_billed(self, in_memory_db):
        contract = self._contract_with_setup_fee(in_memory_db)
        setup_fee = next(c for c in contract.charges if c.basis == ChargeBasis.once)
        self._bill(in_memory_db, contract, setup_fee)

        eligible = InvoicingIntent()._eligible_charges(contract)
        assert [c.description for c in eligible] == ["Daily allowance"]

    def test_a_cancelled_invoice_does_not_consume_the_charge(self, in_memory_db):
        """Voiding the invoice means the fee was never really charged."""
        contract = self._contract_with_setup_fee(in_memory_db)
        setup_fee = next(c for c in contract.charges if c.basis == ChargeBasis.once)
        self._bill(in_memory_db, contract, setup_fee, cancelled=True)

        eligible = InvoicingIntent()._eligible_charges(contract)
        assert [c.description for c in eligible] == ["Daily allowance", "Setup fee"]

    def test_recurring_charges_are_never_consumed(self, in_memory_db):
        contract = self._contract_with_setup_fee(in_memory_db)
        allowance = next(c for c in contract.charges if c.basis == ChargeBasis.per_unit)
        self._bill(in_memory_db, contract, allowance)

        eligible = InvoicingIntent()._eligible_charges(contract)
        assert "Daily allowance" in [c.description for c in eligible]

    def test_the_rpc_preview_reports_the_same_set(self, in_memory_db):
        """The invoice dialog must not advertise a fee that is already spent."""
        contract = self._contract_with_setup_fee(in_memory_db)
        with Session(in_memory_db) as session:
            project = Project(
                title="Retrofit",
                description="On-site retrofit",
                tag="#retrofit",
                contract_id=contract.id,
                start_date=datetime.date(2026, 1, 1),
            )
            session.add(project)
            session.commit()
            project_id = project.id

        intent = InvoicingIntent()
        before = intent.get_eligible_charges(project_id)
        assert [c.description for c in before.data] == ["Daily allowance", "Setup fee"]

        setup_fee = next(c for c in contract.charges if c.basis == ChargeBasis.once)
        self._bill(in_memory_db, contract, setup_fee)

        after = InvoicingIntent().get_eligible_charges(project_id)
        assert [c.description for c in after.data] == ["Daily allowance"]

    def test_the_rpc_preview_is_empty_for_an_unknown_project(self, in_memory_db):
        result = InvoicingIntent().get_eligible_charges(9999)
        assert result.was_intent_successful
        assert result.data == []
