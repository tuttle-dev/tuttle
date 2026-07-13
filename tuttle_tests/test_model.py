"""Tests for the database model."""

import datetime
import os
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.model import (
    Address,
    Client,
    ClientContact,
    Contact,
    Contract,
    InvoiceItem,
    Project,
    TaxCategory,
    User,
    TimeUnit,
    Cycle,
    normalize_tax_category,
)


def store_and_retrieve(model_object):
    # in-memory sqlite db
    db_engine = create_engine("sqlite:///")
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        session.add(model_object)
        session.commit()
    with Session(db_engine) as session:
        session.exec((select(type(model_object)))).first()
    return True


def test_model_creation():
    """Test whether the entire data model can be materialized as DB tables."""
    try:
        test_home = Path("tuttle_tests/data/tmp")
        db_path = test_home / "tuttle_test.db"
        db_url = f"sqlite:///{db_path}"
        db_engine = create_engine(db_url, echo=True)
        SQLModel.metadata.create_all(db_engine)

        # test if database intact
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name;
            """
        )
        cursor.fetchall()
        conn.close()
    finally:
        try:
            os.remove(db_path)
        except OSError:
            pass


class TestUser:
    """Tests for the User model."""

    def test_valid_instantiation(self):
        User.validate(
            dict(
                name="Harry Tuttle",
                subtitle="Heating Engineer",
                email="harry@tuttle.com",
            )
        )


class TestContact:
    def test_valid_instantiation(self):
        contact = Contact.validate(
            dict(
                first_name="Sam",
                last_name="Lowry",
                email="sam.lowry@miniinf.gov",
                company="Ministry of Information",
            )
        )
        assert store_and_retrieve(contact)

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            Contact.validate(
                dict(
                    first_name="Sam",
                    last_name="Lowry",
                    email="27B-",
                    company="Ministry of Information",
                )
            )


class TestClient:
    """Tests for the Client model."""

    def test_valid_instantiation_with_contact(self):
        invoicing_contact = Contact(
            first_name="Sam",
            last_name="Lowry",
            email="sam.lowry@miniinf.gov",
            company="Ministry of Information",
        )
        client = Client(
            name="Ministry of Information",
            invoicing_contact=invoicing_contact,
        )
        db_engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(db_engine)
        with Session(db_engine) as session:
            session.add(invoicing_contact)
            session.add(client)
            session.commit()
        with Session(db_engine) as session:
            retrieved = session.exec(select(Client)).first()
            assert retrieved is not None
            assert retrieved.name == "Ministry of Information"
            assert retrieved.invoicing_contact is not None

    def test_valid_instantiation_with_address(self):
        addr = Address(
            street="Main Street",
            number="42",
            city="Somewhere",
            postal_code="55555",
            country="Brazil",
        )
        client = Client(name="Central Services", address=addr)
        db_engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(db_engine)
        with Session(db_engine) as session:
            session.add(client)
            session.commit()
        with Session(db_engine) as session:
            retrieved = session.exec(select(Client)).first()
            assert retrieved is not None
            assert retrieved.name == "Central Services"
            assert retrieved.invoicing_contact is None
            assert retrieved.address is not None

    def test_invoice_recipient_properties(self):
        addr = Address(
            street="A St", number="1", city="C", postal_code="0", country="X"
        )
        contact_addr = Address(
            street="B St", number="2", city="D", postal_code="1", country="Y"
        )
        contact = Contact(
            first_name="Sam",
            last_name="Lowry",
            email="sam@example.com",
            address=contact_addr,
        )

        client_no_contact = Client(name="Acme Corp", address=addr)
        assert client_no_contact.invoice_recipient_name == "Acme Corp"
        assert client_no_contact.invoice_recipient_address is addr

        client_with_contact = Client(
            name="Acme Corp", address=addr, invoicing_contact=contact
        )
        assert client_with_contact.invoice_recipient_name == "Sam Lowry"
        assert client_with_contact.invoice_recipient_address is contact_addr

    def test_missing_name(self):
        """Test that a ValidationError is raised when the name is missing."""
        with pytest.raises(ValidationError):
            Client.validate(dict())

        try:
            Client.validate(dict())
        except ValidationError as ve:
            for error in ve.errors():
                field_name = error.get("loc")[0]
                assert field_name == "name"

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Client.validate(dict())


class TestClientContact:
    """Tests for the ClientContact many-to-many association."""

    def test_basic_association(self):
        """A contact can be linked to a client with a role."""
        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            contact = Contact(first_name="Sam", last_name="Lowry")
            client = Client(name="Acme Corp")
            s.add_all([contact, client])
            s.commit()
            s.refresh(contact)
            s.refresh(client)
            cid, ctid = client.id, contact.id
            s.add(ClientContact(client_id=cid, contact_id=ctid, role="invoicing"))
            s.commit()
        with Session(engine) as s:
            rows = s.exec(select(ClientContact)).all()
            assert len(rows) == 1
            assert rows[0].role == "invoicing"
            assert rows[0].client_id == cid
            assert rows[0].contact_id == ctid

    def test_multiple_contacts_per_client(self):
        """A client can have multiple contact associations."""
        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            c1 = Contact(first_name="Alice", last_name="A")
            c2 = Contact(first_name="Bob", last_name="B")
            client = Client(name="MultiCo")
            s.add_all([c1, c2, client])
            s.commit()
            s.refresh(c1)
            s.refresh(c2)
            s.refresh(client)
            client_id = client.id
            s.add(ClientContact(client_id=client.id, contact_id=c1.id, role="lead"))
            s.add(ClientContact(client_id=client.id, contact_id=c2.id, role="billing"))
            s.commit()
        with Session(engine) as s:
            cl = s.get(Client, client_id)
            assert len(cl.client_contacts) == 2
            roles = {a.role for a in cl.client_contacts}
            assert roles == {"lead", "billing"}

    def test_multiple_clients_per_contact(self):
        """A contact can represent multiple clients."""
        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            contact = Contact(first_name="Eve", last_name="E")
            cl1 = Client(name="Foo Inc")
            cl2 = Client(name="Bar Ltd")
            s.add_all([contact, cl1, cl2])
            s.commit()
            s.refresh(contact)
            s.refresh(cl1)
            s.refresh(cl2)
            contact_id, cl1_id, cl2_id = contact.id, cl1.id, cl2.id
            s.add(ClientContact(client_id=cl1_id, contact_id=contact_id, role="CEO"))
            s.add(ClientContact(client_id=cl2_id, contact_id=contact_id, role="CEO"))
            s.commit()
        with Session(engine) as s:
            ct = s.get(Contact, contact_id)
            assert len(ct.client_contacts) == 2
            client_ids = {a.client_id for a in ct.client_contacts}
            assert client_ids == {cl1_id, cl2_id}

    def test_cascade_delete_client(self):
        """Deleting a client cascades to its ClientContact rows."""
        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            contact = Contact(first_name="Z", last_name="Z")
            client = Client(name="Gone Corp")
            s.add_all([contact, client])
            s.commit()
            s.refresh(contact)
            s.refresh(client)
            client_id, contact_id = client.id, contact.id
            s.add(ClientContact(client_id=client_id, contact_id=contact_id))
            s.commit()
        with Session(engine) as s:
            cl = s.get(Client, client_id)
            s.delete(cl)
            s.commit()
        with Session(engine) as s:
            assert s.exec(select(ClientContact)).first() is None
            assert s.get(Contact, contact_id) is not None

    def test_role_is_optional(self):
        """Association works without a role."""
        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            contact = Contact(first_name="No", last_name="Role")
            client = Client(name="Roleless Inc")
            s.add_all([contact, client])
            s.commit()
            s.refresh(contact)
            s.refresh(client)
            s.add(ClientContact(client_id=client.id, contact_id=contact.id))
            s.commit()
        with Session(engine) as s:
            row = s.exec(select(ClientContact)).first()
            assert row.role is None


class TestContract:
    """Tests for the Contract model."""

    def test_valid_instantiation(self):
        client = Client(name="Ministry of Information")
        contract = Contract.validate(
            dict(
                title="Project X Contract",
                client=client,
                signature_date=datetime.date(2022, 10, 1),
                start_date=datetime.date(2022, 10, 2),
                end_date=datetime.date(2022, 12, 31),
                rate=100,
                is_completed=False,
                currency="USD",
                VAT_rate=0.19,
                unit=TimeUnit.hour,
                units_per_workday=8,
                volume=100,
                term_of_payment=31,
                billing_cycle=Cycle.monthly,
            )
        )
        assert store_and_retrieve(contract)

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Contract.validate(dict())


class TestProject:
    """Tests for the Project model."""

    def test_valid_instantiation(self):
        client = Client(name="Ministry of Information")
        contract = Contract(
            title="Project X Contract",
            client=client,
            signature_date=datetime.date(2022, 10, 1),
            start_date=datetime.date(2022, 10, 2),
            end_date=datetime.date(2022, 12, 31),
            rate=100,
            is_completed=False,
            currency="USD",
            VAT_rate=0.19,
            unit=TimeUnit.hour,
            units_per_workday=8,
            volume=100,
            term_of_payment=31,
            billing_cycle=Cycle.monthly,
        )
        project = Project.validate(
            dict(
                title="Project X",
                description="The description of Project X",
                tag="#project_x",
                start_date=datetime.date(2022, 10, 2),
                end_date=datetime.date(2022, 12, 31),
                contract=contract,
            )
        )
        assert store_and_retrieve(project)

    def test_missing_fields_instantiation(self):
        with pytest.raises(ValidationError):
            Project.validate(dict())

    def test_invalid_tag_instantiation(self):
        with pytest.raises(ValidationError):
            Project.validate(
                dict(
                    title="Project X",
                    description="The description of Project X",
                    tag="project_x",
                    start_date=datetime.date(2022, 10, 2),
                    end_date=datetime.date(2022, 12, 31),
                )
            )


# ---------------------------------------------------------------------------
# Deletion guard / referential integrity tests
# ---------------------------------------------------------------------------


def _make_engine_with_fk(tmp_path):
    """Create an in-memory SQLite engine with FK enforcement enabled."""
    import sqlalchemy as sa

    db_path = tmp_path / "integrity_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    sa.event.listen(
        engine, "connect", lambda c, _: c.execute("PRAGMA foreign_keys = ON")
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _seed(session):
    """Insert a minimal entity chain: Address -> Contact -> Client -> Contract -> Project."""
    from tuttle.model import Cycle, TimeUnit

    addr = Address(
        street="1st St", number="1", city="C", postal_code="00000", country="US"
    )
    contact = Contact(
        first_name="Jane", last_name="Doe", email="jane@example.com", address=addr
    )
    client = Client(name="Acme", invoicing_contact=contact)
    contract = Contract(
        title="Support",
        client=client,
        signature_date=datetime.date(2024, 1, 1),
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2024, 12, 31),
        rate=100,
        currency="EUR",
        billing_cycle=Cycle.monthly,
        unit=TimeUnit.hour,
    )
    project = Project(
        title="Website",
        description="Build a website",
        tag="#website",
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2024, 6, 30),
        contract=contract,
    )
    session.add(project)
    session.commit()
    session.refresh(contact)
    session.refresh(client)
    session.refresh(contract)
    session.refresh(project)
    return contact, client, contract, project


class TestDeletionGuards:
    """Verify that entities referenced by others cannot be deleted."""

    def test_cannot_delete_contact_used_by_client(self, tmp_path):
        engine = _make_engine_with_fk(tmp_path)
        with Session(engine, expire_on_commit=False) as s:
            contact, client, _, _ = _seed(s)
        with Session(engine) as s:
            c = s.get(Contact, contact.id)
            s.delete(c)
            with pytest.raises(Exception):
                s.commit()

    def test_cannot_delete_client_used_by_contract(self, tmp_path):
        engine = _make_engine_with_fk(tmp_path)
        with Session(engine, expire_on_commit=False) as s:
            _, client, _, _ = _seed(s)
        with Session(engine) as s:
            c = s.get(Client, client.id)
            s.delete(c)
            with pytest.raises(Exception):
                s.commit()

    def test_cannot_delete_contract_used_by_project(self, tmp_path):
        engine = _make_engine_with_fk(tmp_path)
        with Session(engine, expire_on_commit=False) as s:
            _, _, contract, _ = _seed(s)
        with Session(engine) as s:
            c = s.get(Contract, contract.id)
            s.delete(c)
            with pytest.raises(Exception):
                s.commit()

    def test_can_delete_project_without_references(self, tmp_path):
        engine = _make_engine_with_fk(tmp_path)
        with Session(engine, expire_on_commit=False) as s:
            _, _, _, project = _seed(s)
        with Session(engine) as s:
            p = s.get(Project, project.id)
            s.delete(p)
            s.commit()
            assert s.get(Project, project.id) is None

    def test_can_delete_leaf_to_root_sequentially(self, tmp_path):
        """Deleting in reverse dependency order must succeed."""
        engine = _make_engine_with_fk(tmp_path)
        with Session(engine, expire_on_commit=False) as s:
            contact, client, contract, project = _seed(s)
        with Session(engine) as s:
            s.delete(s.get(Project, project.id))
            s.commit()
        with Session(engine) as s:
            s.delete(s.get(Contract, contract.id))
            s.commit()
        with Session(engine) as s:
            s.delete(s.get(Client, client.id))
            s.commit()
        with Session(engine) as s:
            s.delete(s.get(Contact, contact.id))
            s.commit()


class TestTaxCategory:
    """Tax category coercion and the rate/category invariant (EN16931 BR-O/BR-Z)."""

    @staticmethod
    def _contract(**kwargs) -> Contract:
        defaults = dict(
            title="Third-country services",
            start_date=datetime.date(2024, 1, 1),
            currency="EUR",
        )
        return Contract(**{**defaults, **kwargs})

    def test_defaults_to_standard(self):
        assert self._contract().VAT_category is TaxCategory.standard

    def test_untndid_codes_are_the_enum_values(self):
        """The values go straight into the e-invoice XML, so they must be codes."""
        assert TaxCategory.standard.value == "S"
        assert TaxCategory.zero_rated.value == "Z"
        assert TaxCategory.outside_scope.value == "O"

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("O", TaxCategory.outside_scope),
            ("outside_scope", TaxCategory.outside_scope),
            (TaxCategory.outside_scope, TaxCategory.outside_scope),
            ("S", TaxCategory.standard),
            ("zero_rated", TaxCategory.zero_rated),
        ],
    )
    def test_normalize_accepts_codes_names_and_members(self, value, expected):
        assert normalize_tax_category(value) is expected

    @pytest.mark.parametrize("value", [None, "", "X", "bogus"])
    def test_normalize_rejects_unknown(self, value):
        with pytest.raises(ValueError):
            normalize_tax_category(value)

    def test_validate_vat_normalizes_rate_and_category(self):
        contract = self._contract(VAT_rate=19, VAT_category="S")
        contract.validate_vat()
        assert contract.VAT_rate == Decimal("0.19")
        assert contract.VAT_category is TaxCategory.standard

    def test_outside_scope_requires_zero_rate(self):
        contract = self._contract(VAT_rate=Decimal("0.19"), VAT_category="O")
        with pytest.raises(ValueError, match="must be 0 for tax category 'O'"):
            contract.validate_vat()

    def test_zero_rated_requires_zero_rate(self):
        contract = self._contract(VAT_rate=Decimal("0.19"), VAT_category="Z")
        with pytest.raises(ValueError, match="must be 0 for tax category 'Z'"):
            contract.validate_vat()

    def test_outside_scope_with_zero_rate_is_valid(self):
        contract = self._contract(VAT_rate=Decimal("0"), VAT_category="O")
        contract.validate_vat()
        assert contract.VAT_category is TaxCategory.outside_scope

    @pytest.mark.parametrize("order", ["rate_first", "category_first"])
    def test_switching_back_to_standard_is_order_independent(self, order):
        """save_from_dict assigns attributes in payload order; neither may trip."""
        contract = self._contract(VAT_rate=Decimal("0"), VAT_category="O")
        contract.validate_vat()
        if order == "rate_first":
            contract.VAT_rate = Decimal("0.19")
            contract.VAT_category = "S"
        else:
            contract.VAT_category = "S"
            contract.VAT_rate = Decimal("0.19")
        contract.validate_vat()
        assert contract.VAT_category is TaxCategory.standard
        assert contract.VAT_rate == Decimal("0.19")

    def test_invoice_item_carries_its_own_category(self):
        item = InvoiceItem(
            quantity=1, unit="hour", unit_price=Decimal("100"),
            description="work", VAT_rate=Decimal("0"), VAT_category="O",
        )
        item.validate_vat()
        assert item.VAT_category is TaxCategory.outside_scope

    def test_category_survives_a_database_round_trip(self):
        contract = self._contract(VAT_rate=Decimal("0"), VAT_category="O")
        contract.validate_vat()

        engine = create_engine("sqlite:///")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(contract)
            session.commit()
        with Session(engine) as session:
            restored = session.exec(select(Contract)).one()
            assert restored.VAT_category is TaxCategory.outside_scope
