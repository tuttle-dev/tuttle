"""Tests for tuttle.app.tasks.generator."""

import datetime
from decimal import Decimal

import pytest
import sqlmodel

from tuttle.model import (
    Address,
    Client,
    Contact,
    Contract,
    Invoice,
    InvoiceItem,
    Project,
    Task,
)
from tuttle.time import Cycle, TimeUnit
from tuttle.app.tasks.generator import generate_tasks


@pytest.fixture
def session():
    engine = sqlmodel.create_engine("sqlite://", echo=False)
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


# ---------------------------------------------------------------------------
# Tutorial tasks
# ---------------------------------------------------------------------------


class TestTutorialTasks:
    def test_creates_tutorial_tasks_when_empty(self, session):
        generate_tasks(session)
        tasks = session.exec(sqlmodel.select(Task)).all()
        keys = {t.key for t in tasks}
        assert "tutorial:first_contact" in keys
        assert "tutorial:first_client" in keys
        assert "tutorial:first_contract" in keys
        assert "tutorial:first_project" in keys
        assert "tutorial:first_invoice" in keys
        assert all(t.status == "pending" for t in tasks)

    def test_auto_resolves_when_contact_exists(self, session):
        session.add(Contact(first_name="Alice", last_name="Test", email="a@b.com"))
        session.commit()
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == "tutorial:first_contact")
        ).first()
        assert task.status == "done"

    def test_auto_resolves_when_client_exists(self, session):
        session.add(Client(name="Acme Corp"))
        session.commit()
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == "tutorial:first_client")
        ).first()
        assert task.status == "done"

    def test_reopens_if_data_deleted(self, session):
        # First: add contact → task resolved
        contact = Contact(first_name="Bob", last_name="X", email="b@x.com")
        session.add(contact)
        session.commit()
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == "tutorial:first_contact")
        ).first()
        assert task.status == "done"

        # Now delete contact → task should reopen
        session.delete(contact)
        session.commit()
        generate_tasks(session)
        session.refresh(task)
        assert task.status == "pending"

    def test_idempotent_multiple_calls(self, session):
        generate_tasks(session)
        generate_tasks(session)
        generate_tasks(session)
        tasks = session.exec(sqlmodel.select(Task)).all()
        keys = [t.key for t in tasks]
        # No duplicates
        assert len(keys) == len(set(keys))

    def test_manual_tutorial_tasks_created(self, session):
        generate_tasks(session)
        tasks = session.exec(sqlmodel.select(Task)).all()
        keys = {t.key for t in tasks}
        assert "tutorial:configure_ai" in keys
        assert "tutorial:import_document" in keys

    def test_manual_tutorial_tasks_not_auto_resolved(self, session):
        """Manual tutorial tasks stay pending regardless of other data."""
        session.add(Contact(first_name="X", last_name="Y", email="x@y.com"))
        session.commit()
        generate_tasks(session)
        ai_task = session.exec(
            sqlmodel.select(Task).where(Task.key == "tutorial:configure_ai")
        ).first()
        assert ai_task.status == "pending"


# ---------------------------------------------------------------------------
# Overdue invoice tasks
# ---------------------------------------------------------------------------


class TestOverdueTasks:
    @pytest.fixture
    def overdue_invoice(self, session):
        contact = Contact(
            first_name="C",
            last_name="D",
            email="c@d.com",
            address=Address(
                street="S", number="1", postal_code="12345", city="Berlin", country="DE"
            ),
        )
        client = Client(name="OverdueCorp", invoicing_contact=contact)
        contract = Contract(
            title="Test Contract",
            client=client,
            rate=Decimal("100"),
            currency="EUR",
            unit=TimeUnit.hour,
            units_per_workday=8,
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
            start_date=datetime.date(2025, 1, 1),
        )
        project = Project(
            title="Test Project",
            tag="#TestProj",
            description="desc",
            contract=contract,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
        )
        invoice = Invoice(
            number="2025-001",
            date=datetime.date(2025, 1, 1),
            contract=contract,
            project=project,
            sent=True,
            paid=False,
            cancelled=False,
            items=[
                InvoiceItem(
                    quantity=10,
                    unit="h",
                    unit_price=Decimal("100"),
                    description="Work",
                    VAT_rate=Decimal("0.19"),
                )
            ],
        )
        session.add(invoice)
        session.commit()
        return invoice

    def test_creates_overdue_task(self, session, overdue_invoice):
        assert overdue_invoice.status == "overdue"
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == f"overdue:{overdue_invoice.id}")
        ).first()
        assert task is not None
        assert task.status == "pending"
        assert "2025-001" in task.title

    def test_does_not_create_if_reminder_exists(self, session, overdue_invoice):
        # Add a reminder for the invoice
        reminder = Invoice(
            number="2025-001-M1",
            date=datetime.date(2025, 3, 1),
            contract=overdue_invoice.contract,
            project=overdue_invoice.project,
            document_type="reminder",
            reminder_for_id=overdue_invoice.id,
            reminder_level=1,
            sent=True,
            items=[],
        )
        session.add(reminder)
        session.commit()
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == f"overdue:{overdue_invoice.id}")
        ).first()
        assert task is None

    def test_does_not_create_for_paid_invoice(self, session, overdue_invoice):
        overdue_invoice.paid = True
        session.add(overdue_invoice)
        session.commit()
        assert overdue_invoice.status == "paid"
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == f"overdue:{overdue_invoice.id}")
        ).first()
        assert task is None
