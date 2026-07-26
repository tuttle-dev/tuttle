"""Tests for the document import flow (invoice import via commit_import)."""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.imports.intent import ImportsIntent, _model_fields
from tuttle.model import (
    Address,
    Client,
    Contract,
    Invoice,
    InvoiceItem,
    Project,
)
from tuttle.time import ContractType


@pytest.fixture
def in_memory_db(monkeypatch):
    """Set up an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    def _create_session(self):
        return Session(engine)

    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", _create_session)
    return engine


class TestInvoiceImport:
    def test_commit_invoice_basic(self, in_memory_db):
        """Import a basic invoice with line items."""
        intent = ImportsIntent()

        data = {
            "contacts": [],
            "clients": [{"ref": "client_1", "name": "Acme Corp"}],
            "contracts": [
                {
                    "ref": "contract_1",
                    "title": "Web Development",
                    "client_ref": "client_1",
                    "rate": 100.0,
                    "currency": "EUR",
                    "unit": "hour",
                    "billing_cycle": "monthly",
                    "volume": 160,
                    "start_date": "2024-01-01",
                    "VAT_rate": 0.19,
                    "term_of_payment": 14,
                }
            ],
            "projects": [
                {
                    "ref": "project_1",
                    "title": "Website Redesign",
                    "description": "Full redesign of company website",
                    "tag": "#WebRedesign",
                    "contract_ref": "contract_1",
                    "start_date": "2024-01-01",
                    "end_date": "2024-06-30",
                }
            ],
            "invoices": [
                {
                    "ref": "invoice_1",
                    "number": "2024-01-01",
                    "date": "2024-01-31",
                    "notes": "Thank you for your business.",
                    "contract_ref": "contract_1",
                    "project_ref": "project_1",
                    "sent": True,
                    "paid": False,
                    "items": [
                        {
                            "description": "Frontend development",
                            "quantity": 40.0,
                            "unit": "hour",
                            "unit_price": 100.0,
                            "VAT_rate": 0.19,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                        {
                            "description": "Backend development",
                            "quantity": 20.0,
                            "unit": "hour",
                            "unit_price": 100.0,
                            "VAT_rate": 0.19,
                            "start_date": "2024-01-01",
                            "end_date": "2024-01-31",
                        },
                    ],
                }
            ],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        summary = result.data
        assert "Invoice: 2024-01-01" in summary["created"]
        assert any("Acme Corp" in s for s in summary["created"])
        assert any("Web Development" in s for s in summary["created"])

        # Verify DB state
        with Session(in_memory_db) as session:
            invoices = session.exec(select(Invoice)).all()
            assert len(invoices) == 1
            inv = invoices[0]
            assert inv.number == "2024-01-01"
            assert inv.date == datetime.date(2024, 1, 31)
            assert inv.sent is True
            assert inv.paid is False
            assert inv.rendered is True
            assert inv.notes == "Thank you for your business."
            assert inv.contract_id is not None
            assert inv.project_id is not None

            items = session.exec(select(InvoiceItem)).all()
            assert len(items) == 2
            assert items[0].quantity == 40.0
            assert items[0].unit_price == Decimal("100.0")
            assert items[1].quantity == 20.0

    def test_commit_invoice_with_existing_contract(self, in_memory_db):
        """Import an invoice linked to an existing DB contract via existing:ID."""
        with Session(in_memory_db) as session:
            client = Client(name="Existing Client")
            session.add(client)
            session.flush()
            contract = Contract(
                title="Existing Contract",
                client_id=client.id,
                rate=Decimal("80"),
                currency="EUR",
                unit="hour",
                start_date=datetime.date(2023, 1, 1),
            )
            session.add(contract)
            session.flush()
            project = Project(
                title="Existing Project",
                description="Project for testing",
                tag="#ExistingProj",
                contract_id=contract.id,
                start_date=datetime.date(2023, 1, 1),
                end_date=datetime.date(2023, 12, 31),
            )
            session.add(project)
            session.commit()
            contract_id = contract.id
            project_id = project.id

        intent = ImportsIntent()
        data = {
            "contacts": [],
            "clients": [],
            "contracts": [],
            "projects": [],
            "invoices": [
                {
                    "ref": "invoice_1",
                    "number": "2024-03-15",
                    "date": "2024-03-15",
                    "contract_ref": f"existing:{contract_id}",
                    "project_ref": f"existing:{project_id}",
                    "items": [
                        {
                            "description": "Consulting",
                            "quantity": 8.0,
                            "unit": "hour",
                            "unit_price": 80.0,
                            "VAT_rate": 0.19,
                            "start_date": "2024-03-15",
                            "end_date": "2024-03-15",
                        },
                    ],
                }
            ],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        with Session(in_memory_db) as session:
            inv = session.exec(select(Invoice)).first()
            assert inv.contract_id == contract_id
            assert inv.project_id == project_id

    def test_commit_invoice_no_items_validates(self, in_memory_db):
        """An invoice with no items still persists (validation is UI-side)."""
        intent = ImportsIntent()
        data = {
            "contacts": [],
            "clients": [],
            "contracts": [],
            "projects": [],
            "invoices": [
                {
                    "ref": "invoice_1",
                    "number": "EMPTY-001",
                    "date": "2024-05-01",
                    "contract_ref": "",
                    "project_ref": "",
                    "items": [],
                }
            ],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        with Session(in_memory_db) as session:
            inv = session.exec(select(Invoice)).first()
            assert inv.number == "EMPTY-001"
            assert inv.contract_id is None

    def test_model_fields_coercion(self):
        """Test that _model_fields correctly coerces invoice types."""
        data = {
            "number": "2024-01",
            "date": "2024-01-31",
            "sent": True,
            "rendered": True,
            "notes": "Hello",
            "ref": "should_be_excluded",
            "items": "should_be_excluded",
            "contract_ref": "should_be_excluded",
        }
        fields = _model_fields(data, Invoice)
        assert "ref" not in fields
        assert "items" not in fields
        assert "contract_ref" not in fields
        assert fields["number"] == "2024-01"
        assert fields["date"] == datetime.date(2024, 1, 31)
        assert fields["sent"] is True

    def test_validation_catches_missing_required_fields(self, in_memory_db):
        """Required fields are validated before DB insertion."""
        intent = ImportsIntent()
        data = {
            "contacts": [],
            "clients": [{"ref": "client_1", "name": "Acme"}],
            "contracts": [
                {
                    "ref": "contract_1",
                    "title": "Dev Contract",
                    "client_ref": "client_1",
                    "rate": 100.0,
                    "currency": "EUR",
                    "start_date": "2024-01-01",
                }
            ],
            "projects": [
                {
                    "ref": "project_1",
                    "title": "My Project",
                    "contract_ref": "contract_1",
                    "start_date": "2024-01-01",
                }
            ],
            "invoices": [],
        }

        result = intent.commit_import(data)
        assert not result.was_intent_successful
        msg = result.error_msg.lower()
        # Project missing fields (labels derived from model field names)
        assert "description" in msg
        assert "tag" in msg

    def test_validation_skips_existing_entities(self, in_memory_db):
        """Entities with existing_id skip validation (they're link-only)."""
        intent = ImportsIntent()
        data = {
            "contacts": [],
            "clients": [],
            "contracts": [],
            "projects": [
                {
                    "ref": "project_1",
                    "existing_id": 999,
                    "title": "Incomplete",
                }
            ],
            "invoices": [],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

    def test_vat_rate_percent_normalized_on_save(self, in_memory_db):
        """VAT_rate given as percent (e.g. 19) is normalized to 0.19 in the DB."""
        intent = ImportsIntent()
        data = {
            "contacts": [],
            "clients": [],
            "contracts": [],
            "projects": [],
            "invoices": [
                {
                    "ref": "inv_1",
                    "number": "VAT-PCT-001",
                    "date": "2024-06-01",
                    "contract_ref": "",
                    "project_ref": "",
                    "items": [
                        {
                            "description": "Consulting",
                            "quantity": 10.0,
                            "unit": "hour",
                            "unit_price": 100.0,
                            "VAT_rate": 19,
                        }
                    ],
                }
            ],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        with Session(in_memory_db) as session:
            item = session.exec(select(InvoiceItem)).one()
            assert item.VAT_rate == Decimal("0.19")
            assert item.subtotal == Decimal("1000")
            assert item.VAT == Decimal("190.0")

    def test_validation_catches_implausible_vat_rate(self, in_memory_db):
        """A VAT rate above 30% triggers a plausibility warning."""
        from tuttle.app.imports.intent import _validate_import_data

        data = {
            "contacts": [],
            "clients": [],
            "contracts": [],
            "projects": [],
            "invoices": [
                {
                    "number": "BAD-VAT",
                    "date": "2024-01-01",
                    "items": [
                        {
                            "description": "Item",
                            "quantity": 1.0,
                            "unit": "hour",
                            "unit_price": 100.0,
                            "VAT_rate": 0.50,
                        }
                    ],
                }
            ],
        }
        errors = _validate_import_data(data)
        assert any("implausibly high" in e for e in errors)

    def test_validation_catches_negative_unit_price(self, in_memory_db):
        """Negative unit price is flagged."""
        from tuttle.app.imports.intent import _validate_import_data

        data = {
            "contacts": [],
            "clients": [],
            "contracts": [],
            "projects": [],
            "invoices": [
                {
                    "number": "NEG-001",
                    "date": "2024-01-01",
                    "items": [
                        {
                            "description": "Credit?",
                            "quantity": 1.0,
                            "unit": "piece",
                            "unit_price": -50.0,
                            "VAT_rate": 0.19,
                        }
                    ],
                }
            ],
        }
        errors = _validate_import_data(data)
        assert any("negative" in e for e in errors)


class TestClientAddressImport:
    """Regression guard: client address extraction must persist an Address row."""

    def test_commit_client_with_address(self, in_memory_db):
        """Import a client with a nested address dict creates Address + Client."""
        intent = ImportsIntent()

        data = {
            "contacts": [],
            "clients": [
                {
                    "ref": "client_1",
                    "name": "Acme Corp",
                    "vat_number": "DE123456789",
                    "address": {
                        "street": "Hauptstraße",
                        "number": "42",
                        "city": "Berlin",
                        "postal_code": "10115",
                        "country": "Germany",
                    },
                }
            ],
            "contracts": [],
            "projects": [],
            "invoices": [],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        with Session(in_memory_db) as session:
            client = session.exec(select(Client)).one()
            assert client.name == "Acme Corp"
            assert client.vat_number == "DE123456789"
            assert client.address_id is not None

            addr = session.get(Address, client.address_id)
            assert addr is not None
            assert addr.street == "Hauptstraße"
            assert addr.number == "42"
            assert addr.city == "Berlin"
            assert addr.postal_code == "10115"
            assert addr.country == "Germany"

    def test_commit_client_without_address(self, in_memory_db):
        """A client with no address dict still imports fine."""
        intent = ImportsIntent()

        data = {
            "contacts": [],
            "clients": [{"ref": "client_1", "name": "No Address Inc"}],
            "contracts": [],
            "projects": [],
            "invoices": [],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        with Session(in_memory_db) as session:
            client = session.exec(select(Client)).one()
            assert client.name == "No Address Inc"
            assert client.address_id is None


class TestContractPricingInvariant:
    """A contract is time-based XOR fixed-price — never both, never neither.

    Regression guard for the document-import path, which builds Contract
    rows directly (bypassing ContractsIntent) and let an LLM-extracted
    contract carry BOTH a rate and a fixed price into the database.
    """

    def _base_contract(self, **overrides):
        data = {
            "ref": "contract_1",
            "title": "Ambiguous Contract",
            "currency": "EUR",
            "unit": "day",
            "billing_cycle": "monthly",
            "volume": 10,
            "start_date": "2026-06-10",
            "end_date": "2026-07-10",
            "VAT_rate": 0.19,
            "term_of_payment": 14,
        }
        data.update(overrides)
        return data

    def test_both_rate_and_fixed_price_is_normalised(self, in_memory_db):
        """The exact reported bug: an extracted contract with both a fixed
        price and a day rate must persist as a single, unambiguous type."""
        intent = ImportsIntent()
        data = {
            "contacts": [],
            "clients": [],
            "contracts": [self._base_contract(type="fixed_price", fixed_price=2000.0, rate=1000.0)],
            "projects": [],
            "invoices": [],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        with Session(in_memory_db) as session:
            c = session.exec(select(Contract)).one()
            assert c.is_fixed_price
            assert c.fixed_price == Decimal("2000")
            # The contradictory rate must have been cleared.
            assert c.rate is None

    def test_type_derived_when_absent(self, in_memory_db):
        """If the LLM omits ``type``, it is derived from the value columns."""
        intent = ImportsIntent()
        data = {
            "contacts": [],
            "clients": [],
            "contracts": [self._base_contract(fixed_price=5000.0)],
            "projects": [],
            "invoices": [],
        }

        result = intent.commit_import(data)
        assert result.was_intent_successful

        with Session(in_memory_db) as session:
            c = session.exec(select(Contract)).one()
            assert c.is_fixed_price
            assert c.rate is None

    def test_validate_pricing_clears_off_column(self):
        """The model method is the single source of truth and self-heals."""
        c = Contract(
            title="X",
            currency="EUR",
            start_date=datetime.date(2026, 1, 1),
            type=ContractType.fixed_price,
            fixed_price=Decimal("2000"),
            rate=Decimal("1000"),
        )
        c.validate_pricing()
        assert c.rate is None
        assert c.fixed_price == Decimal("2000")

    def test_validate_pricing_requires_a_value(self):
        """A fixed-price contract with no fixed price is rejected."""
        c = Contract(
            title="X",
            currency="EUR",
            start_date=datetime.date(2026, 1, 1),
            type=ContractType.fixed_price,
        )
        with pytest.raises(ValueError):
            c.validate_pricing()


class TestLlmInvoiceSchema:
    def test_extraction_schema_includes_invoices(self):
        """Verify the extraction schema has an invoices field."""
        from tuttle.llm import DocumentExtractionResult

        assert "invoices" in DocumentExtractionResult.model_fields

    def test_invoice_extract_model_fields(self):
        """Verify the invoice extraction model has the right fields."""
        from tuttle.llm import _RefInvoice, _RefInvoiceItem

        inv_fields = set(_RefInvoice.model_fields.keys())
        assert "number" in inv_fields
        assert "date" in inv_fields
        assert "notes" in inv_fields
        assert "ref" in inv_fields
        assert "contract_ref" in inv_fields
        assert "project_ref" in inv_fields
        assert "items" in inv_fields

        item_fields = set(_RefInvoiceItem.model_fields.keys())
        assert "quantity" in item_fields
        assert "unit" in item_fields
        assert "unit_price" in item_fields
        assert "description" in item_fields
        assert "VAT_rate" in item_fields
        assert "start_date" in item_fields

    def test_map_invoices(self):
        """Test invoice mapping from extraction result to dict."""
        from tuttle.llm import _map_invoices, _RefInvoice, _RefInvoiceItem

        inv = _RefInvoice(
            ref="invoice_1",
            number="2024-06-01",
            date=datetime.date(2024, 6, 1),
            notes="Test",
            contract_ref="contract_1",
            project_ref="project_1",
            items=[
                _RefInvoiceItem(
                    start_date=datetime.date(2024, 6, 1),
                    end_date=datetime.date(2024, 6, 30),
                    quantity=10.0,
                    unit="hour",
                    unit_price=100.0,
                    description="Dev work",
                    VAT_rate=0.19,
                )
            ],
        )

        result = _map_invoices([inv])
        assert len(result) == 1
        assert result[0]["number"] == "2024-06-01"
        assert result[0]["ref"] == "invoice_1"
        assert len(result[0]["items"]) == 1
        assert result[0]["items"][0]["quantity"] == 10.0
        assert result[0]["items"][0]["start_date"] == "2024-06-01"

    def test_map_invoices_normalizes_vat_rate_percent(self):
        """LLM returning VAT_rate as percent (e.g. 19) must be normalized to fraction."""
        from tuttle.llm import _map_invoices, _RefInvoice, _RefInvoiceItem

        inv = _RefInvoice(
            ref="inv_1",
            number="PCT-001",
            date=datetime.date(2024, 1, 1),
            items=[
                _RefInvoiceItem(
                    quantity=1.0,
                    unit="hour",
                    unit_price=100.0,
                    description="Work",
                    VAT_rate=19,
                )
            ],
        )

        result = _map_invoices([inv])
        vat = result[0]["items"][0]["VAT_rate"]
        assert abs(vat - 0.19) < 1e-6, f"Expected 0.19, got {vat}"

    def test_summary_prompt_includes_invoices(self):
        """Verify the generated summary prompt mentions invoices."""
        from tuttle.llm import _DOC_SUMMARY_PROMPT

        assert "INVOICES" in _DOC_SUMMARY_PROMPT

    def test_summary_prompt_mentions_fixed_price(self):
        """The summary prompt must guide the LLM on fixed-price invoices."""
        from tuttle.llm import _DOC_SUMMARY_PROMPT

        assert "fixed_price" in _DOC_SUMMARY_PROMPT or "fixed-price" in _DOC_SUMMARY_PROMPT

    def test_extract_prompt_mentions_fixed_price(self):
        """The extraction prompt must guide the LLM on fixed-price line items."""
        from tuttle.llm import _DOC_EXTRACT_PROMPT

        assert "fixed_price" in _DOC_EXTRACT_PROMPT

    def test_invoice_item_schema_has_unit_description(self):
        """The LLM schema for invoice items must describe the unit field."""
        from tuttle.llm import _RefInvoiceItem

        unit_info = _RefInvoiceItem.model_fields["unit"]
        assert unit_info.description is not None
        assert "fixed_price" in unit_info.description

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("hour", "hour"),
            ("hours", "hour"),
            ("day", "day"),
            ("days", "day"),
            ("fixed_price", "fixed_price"),
            ("fixed price", "fixed_price"),
            ("Fixed_Price", "fixed_price"),
            (None, None),
            ("widget", "widget"),
        ],
    )
    def test_normalize_unit(self, raw, expected):
        from tuttle.llm import _normalize_unit

        assert _normalize_unit(raw) == expected

    def test_map_invoices_normalizes_unit(self):
        """_map_invoices must normalise trivial unit variations."""
        from tuttle.llm import _map_invoices, _RefInvoice, _RefInvoiceItem

        inv = _RefInvoice(
            ref="inv_fp",
            number="FP-001",
            date=datetime.date(2024, 1, 1),
            items=[
                _RefInvoiceItem(
                    quantity=1.0,
                    unit="fixed price",
                    unit_price=5000.0,
                    description="Project delivery",
                    VAT_rate=0.19,
                )
            ],
        )

        result = _map_invoices([inv])
        assert result[0]["items"][0]["unit"] == "fixed_price"
