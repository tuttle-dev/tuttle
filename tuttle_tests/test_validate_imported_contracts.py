"""A contract imported from a document is checked like one entered by hand.

The import used to save contracts without the contract form's validators (a
document's "19" became a 1900% VAT rate), fill what the document left open with
model defaults (a 31-day term, an hourly unit, a monthly cycle), and drop links
to entities that were not imported without a word.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.contracts.intent import ContractsIntent
from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.imports.intent import ImportsIntent
from tuttle.llm import _with_fraction_vat_rates
from tuttle.model import Client, Contact, Contract, Invoice, Project, TaxCategory
from tuttle.time import Cycle, TimeUnit


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _contract(**overrides) -> dict:
    """A contract as the review sends it, with everything a time-based one needs."""
    contract = {
        "ref": "contract_1",
        "title": "Boiler Service",
        "type": "time_based",
        "rate": 95.0,
        "currency": "EUR",
        "unit": "hour",
        "billing_cycle": "monthly",
        "volume": 40,
        "start_date": "2026-01-01",
        "VAT_rate": 0.19,
        "client_ref": "",
    }
    contract.update(overrides)
    return contract


def _commit(**lists):
    data = {"contacts": [], "clients": [], "contracts": [], "projects": [], "invoices": []}
    data.update(lists)
    return ImportsIntent().commit_import(data)


def _contracts(engine) -> list[Contract]:
    with Session(engine) as session:
        return session.exec(select(Contract)).all()


class TestValidators:
    def test_a_documents_percentage_is_stored_as_a_fraction(self, in_memory_db):
        assert _with_fraction_vat_rates([{"VAT_rate": 19}]) == [{"VAT_rate": 0.19}]
        result = _commit(contracts=[_contract(VAT_rate=19)])
        assert result.was_intent_successful, result.error_msg
        assert _contracts(in_memory_db)[0].VAT_rate == Decimal("0.19")

    def test_an_impossible_vat_rate_is_refused_by_name(self, in_memory_db):
        result = _commit(contracts=[_contract(VAT_rate=250)])
        assert not result.was_intent_successful
        assert result.error_msg.startswith('Contract "Boiler Service": VAT rate 250 is out of range')
        assert _contracts(in_memory_db) == []

    def test_a_rate_outside_the_standard_category_is_refused(self, in_memory_db):
        result = _commit(contracts=[_contract(VAT_category="O")])
        assert result.error_msg.startswith('Contract "Boiler Service": VAT rate must be 0')

    def test_an_unsupported_currency_is_refused_by_name(self, in_memory_db):
        result = _commit(contracts=[_contract(currency="XYZ")])
        assert result.error_msg.startswith('Contract "Boiler Service": ')
        assert "XYZ" in result.error_msg
        assert _contracts(in_memory_db) == []

    def test_a_refused_contract_saves_nothing_of_the_import(self, in_memory_db):
        result = _commit(clients=[{"ref": "client_1", "name": "Sam Lowry"}], contracts=[_contract(VAT_rate=250)])
        assert not result.was_intent_successful
        with Session(in_memory_db) as session:
            assert session.exec(select(Client)).all() == []


class TestUnstatedFields:
    def test_no_payment_term_stays_empty(self, in_memory_db):
        assert _commit(contracts=[_contract()]).was_intent_successful
        assert _contracts(in_memory_db)[0].term_of_payment is None

    def test_a_stated_payment_term_is_kept(self, in_memory_db):
        assert _commit(contracts=[_contract(term_of_payment=14)]).was_intent_successful
        assert _contracts(in_memory_db)[0].term_of_payment == 14

    def test_a_contract_entered_without_a_term_has_none(self, in_memory_db):
        """The model's 31 days used to replace an empty term on insert, on every path."""
        payload = {k: v for k, v in _contract(term_of_payment=None).items() if k not in ("ref", "client_ref")}
        result = ContractsIntent().save_from_dict(payload)
        assert result.was_intent_successful, result.error_msg
        assert _contracts(in_memory_db)[0].term_of_payment is None

    def test_a_time_based_contract_needs_its_unit_and_billing_cycle(self, in_memory_db):
        result = _commit(contracts=[_contract(unit="", billing_cycle=None)])
        assert result.error_msg == 'Contract "Boiler Service": fill in the unit and billing cycle.'
        assert _contracts(in_memory_db) == []

    def test_a_contract_needs_its_vat_rate_currency_and_price(self, in_memory_db):
        result = _commit(contracts=[_contract(VAT_rate=None, currency="", rate=None)])
        assert result.error_msg == 'Contract "Boiler Service": fill in the currency, VAT rate and rate.'

    def test_a_fixed_price_contract_needs_its_price_but_no_unit(self, in_memory_db):
        contract = _contract(type="fixed_price", rate=None, unit=None, billing_cycle=None, volume=None)
        assert _commit(contracts=[contract]).error_msg == 'Contract "Boiler Service": fill in the fixed price.'
        assert _commit(contracts=[{**contract, "fixed_price": 5000.0}]).was_intent_successful

    def test_outside_the_standard_category_the_rate_is_zero(self, in_memory_db):
        assert _commit(contracts=[_contract(VAT_rate=None, VAT_category="O")]).was_intent_successful
        contract = _contracts(in_memory_db)[0]
        assert contract.VAT_rate == 0
        assert contract.VAT_category is TaxCategory.outside_scope

    def test_the_review_learns_what_each_type_needs(self):
        meta = ImportsIntent().get_field_metadata().data["contracts"]
        assert meta["required_by_type"] == {"time_based": ["rate", "unit", "billing_cycle"], "fixed_price": ["fixed_price"]}
        assert "VAT_rate" in meta["required"]


def _existing(engine) -> dict:
    """Ids of a contact, client, contract and project already in the database."""
    with Session(engine) as session:
        contact = Contact(first_name="Jill", last_name="Layton", email="jill@example.com")
        client = Client(name="Central Services")
        contract = Contract(
            title="Retainer",
            client=client,
            start_date=datetime.date(2026, 1, 1),
            rate=Decimal("80"),
            currency="EUR",
            VAT_rate=Decimal("0.19"),
            unit=TimeUnit.hour,
            billing_cycle=Cycle.monthly,
            volume=100,
        )
        project = Project(
            title="Ducts", description="Duct work", tag="#ducts", contract=contract, start_date=datetime.date(2026, 1, 1)
        )
        session.add_all([contact, project])
        session.commit()
        return {"contact": contact.id, "client": client.id, "contract": contract.id, "project": project.id}


class TestLinks:
    def test_a_link_to_a_client_that_is_not_imported_is_refused(self, in_memory_db):
        result = _commit(contracts=[_contract(client_ref="client_1")])
        assert result.error_msg == (
            'Contract "Boiler Service" is linked to a client that is not being imported. '
            "Restore that client or link another one."
        )
        assert _contracts(in_memory_db) == []

    def test_an_invoice_linked_to_a_contract_that_is_not_imported_is_refused(self, in_memory_db):
        invoice = {"ref": "invoice_1", "number": "2026-001", "date": "2026-02-01", "contract_ref": "contract_1", "items": []}
        result = _commit(invoices=[invoice])
        assert result.error_msg == (
            'Invoice "2026-001" is linked to a contract that is not being imported. Restore that contract or link another one.'
        )
        with Session(in_memory_db) as session:
            assert session.exec(select(Invoice)).all() == []

    def test_a_project_needs_a_contract(self, in_memory_db):
        project = {
            "ref": "project_1",
            "title": "Ducts",
            "description": "Duct work",
            "tag": "#ducts",
            "start_date": "2026-01-01",
        }
        result = _commit(projects=[{**project, "contract_ref": ""}])
        assert result.error_msg == 'Project "Ducts" needs a contract. Link one.'

    def test_a_match_to_a_record_that_is_gone_is_refused(self, in_memory_db):
        result = _commit(projects=[{"ref": "project_1", "existing_id": 999, "title": "Ducts"}])
        assert result.error_msg == (
            'Project "Ducts" is matched to an existing project that no longer exists. Create it as a new record or match another project.'
        )

    def test_a_link_to_a_record_that_is_gone_is_refused(self, in_memory_db):
        invoice = {"ref": "invoice_1", "number": "2026-001", "date": "2026-02-01", "contract_ref": "existing:999", "items": []}
        result = _commit(invoices=[invoice])
        assert result.error_msg == 'Invoice "2026-001" is linked to a contract that no longer exists. Link another contract.'

    def test_a_link_to_an_existing_contact_is_kept(self, in_memory_db):
        ids = _existing(in_memory_db)
        client = {"ref": "client_1", "name": "Sam Lowry", "contact_ref": f"existing:{ids['contact']}"}
        assert _commit(clients=[client]).was_intent_successful
        with Session(in_memory_db) as session:
            saved = session.exec(select(Client).where(Client.name == "Sam Lowry")).one()
            assert saved.invoicing_contact_id == ids["contact"]

    def test_a_matched_contract_takes_the_client_it_is_linked_to(self, in_memory_db):
        ids = _existing(in_memory_db)
        contract = {"ref": "contract_1", "existing_id": ids["contract"], "update_existing": True, "client_ref": "client_1"}
        result = _commit(clients=[{"ref": "client_1", "name": "Sam Lowry"}], contracts=[contract])
        assert result.was_intent_successful, result.error_msg
        with Session(in_memory_db) as session:
            assert session.get(Contract, ids["contract"]).client.name == "Sam Lowry"
