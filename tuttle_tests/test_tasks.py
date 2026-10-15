"""Tests for tuttle.app.tasks.generator."""

import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
import sqlmodel

from tuttle.app.tasks.generator import generate_tasks, _parse_lead_days
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


@pytest.fixture
def session():
    engine = sqlmodel.create_engine("sqlite://", echo=False)
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


# ---------------------------------------------------------------------------
# _parse_lead_days
# ---------------------------------------------------------------------------


class TestParseLeadDays:
    def test_simple(self):
        assert _parse_lead_days("30, 7, 0") == [30, 7, 0]

    def test_deduplicates(self):
        assert _parse_lead_days("7, 7, 0") == [7, 0]

    def test_ignores_garbage(self):
        assert _parse_lead_days("30, abc, , -1, 0") == [30, 0]

    def test_empty_string(self):
        assert _parse_lead_days("") == []


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
        task = session.exec(sqlmodel.select(Task).where(Task.key == "tutorial:first_contact")).first()
        assert task.status == "done"

    def test_auto_resolves_when_client_exists(self, session):
        session.add(Client(name="Acme Corp"))
        session.commit()
        generate_tasks(session)
        task = session.exec(sqlmodel.select(Task).where(Task.key == "tutorial:first_client")).first()
        assert task.status == "done"

    def test_reopens_if_data_deleted(self, session):
        # First: add contact → task resolved
        contact = Contact(first_name="Bob", last_name="X", email="b@x.com")
        session.add(contact)
        session.commit()
        generate_tasks(session)
        task = session.exec(sqlmodel.select(Task).where(Task.key == "tutorial:first_contact")).first()
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

    def test_refreshes_outdated_copy(self, session):
        session.add(Task(key="tutorial:configure_ai", title="Old", description="Old text", status="done"))
        session.commit()
        generate_tasks(session)
        task = session.exec(sqlmodel.select(Task).where(Task.key == "tutorial:configure_ai")).first()
        assert task.title == "Configure AI assistant"
        assert task.description != "Old text"
        assert task.status == "done"

    def test_manual_tutorial_tasks_not_auto_resolved(self, session):
        """Manual tutorial tasks stay pending regardless of other data."""
        session.add(Contact(first_name="X", last_name="Y", email="x@y.com"))
        session.commit()
        generate_tasks(session)
        ai_task = session.exec(sqlmodel.select(Task).where(Task.key == "tutorial:configure_ai")).first()
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
            address=Address(street="S", number="1", postal_code="12345", city="Berlin", country="DE"),
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
        task = session.exec(sqlmodel.select(Task).where(Task.key == f"overdue:{overdue_invoice.id}")).first()
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
        task = session.exec(sqlmodel.select(Task).where(Task.key == f"overdue:{overdue_invoice.id}")).first()
        assert task is None

    def test_does_not_create_for_paid_invoice(self, session, overdue_invoice):
        overdue_invoice.paid = True
        session.add(overdue_invoice)
        session.commit()
        assert overdue_invoice.status == "paid"
        generate_tasks(session)
        task = session.exec(sqlmodel.select(Task).where(Task.key == f"overdue:{overdue_invoice.id}")).first()
        assert task is None


# ---------------------------------------------------------------------------
# Contract-end tasks
# ---------------------------------------------------------------------------


class TestContractEndTasks:
    @pytest.fixture
    def ending_contract(self, session):
        client = Client(name="EndCorp")
        contract = Contract(
            title="Ending Contract",
            client=client,
            rate=Decimal("100"),
            currency="EUR",
            unit=TimeUnit.hour,
            units_per_workday=8,
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date.today() + datetime.timedelta(days=10),
        )
        session.add(contract)
        session.commit()
        return contract

    def test_creates_task_within_lead_window(self, session, ending_contract):
        """Contract ending in 10 days triggers a 30-day lead task."""
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == f"contract_ending:{ending_contract.id}:30")
        ).first()
        assert task is not None
        assert "Ending Contract" in task.title

    def test_no_task_outside_lead_window(self, session):
        """Contract ending in 60 days should not trigger 30-day lead task."""
        client = Client(name="FarCorp")
        contract = Contract(
            title="Far Contract",
            client=client,
            rate=Decimal("100"),
            currency="EUR",
            unit=TimeUnit.hour,
            units_per_workday=8,
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date.today() + datetime.timedelta(days=60),
        )
        session.add(contract)
        session.commit()
        generate_tasks(session)
        tasks = session.exec(
            sqlmodel.select(Task).where(Task.key.startswith("contract_ending:"))  # type: ignore[union-attr]
        ).all()
        assert len(tasks) == 0

    def test_no_task_for_completed_contract(self, session, ending_contract):
        ending_contract.is_completed = True
        session.add(ending_contract)
        session.commit()
        generate_tasks(session)
        tasks = session.exec(
            sqlmodel.select(Task).where(Task.key.startswith("contract_ending:"))  # type: ignore[union-attr]
        ).all()
        assert len(tasks) == 0

    def test_no_task_for_open_ended_contract(self, session):
        client = Client(name="OpenCorp")
        contract = Contract(
            title="Open Contract",
            client=client,
            rate=Decimal("100"),
            currency="EUR",
            unit=TimeUnit.hour,
            units_per_workday=8,
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
            start_date=datetime.date(2025, 1, 1),
        )
        session.add(contract)
        session.commit()
        generate_tasks(session)
        tasks = session.exec(
            sqlmodel.select(Task).where(Task.key.startswith("contract_ending:"))  # type: ignore[union-attr]
        ).all()
        assert len(tasks) == 0

    def test_idempotent(self, session, ending_contract):
        generate_tasks(session)
        generate_tasks(session)
        tasks = session.exec(
            sqlmodel.select(Task).where(Task.key == f"contract_ending:{ending_contract.id}:30")
        ).all()
        assert len(tasks) == 1

    @patch("tuttle.app.tasks.generator._load_lead_days")
    def test_custom_lead_days(self, mock_load, session):
        mock_load.return_value = ([7], [0])
        client = Client(name="CustomCorp")
        contract = Contract(
            title="Custom Lead",
            client=client,
            rate=Decimal("100"),
            currency="EUR",
            unit=TimeUnit.hour,
            units_per_workday=8,
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date.today() + datetime.timedelta(days=5),
        )
        session.add(contract)
        session.commit()
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == f"contract_ending:{contract.id}:7")
        ).first()
        assert task is not None

    def test_today_end_date_task(self, session):
        """Contract ending today triggers the 0-day lead task."""
        client = Client(name="TodayCorp")
        contract = Contract(
            title="Today Contract",
            client=client,
            rate=Decimal("100"),
            currency="EUR",
            unit=TimeUnit.hour,
            units_per_workday=8,
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date.today(),
        )
        session.add(contract)
        session.commit()
        generate_tasks(session)
        task = session.exec(
            sqlmodel.select(Task).where(Task.key == f"contract_ending:{contract.id}:0")
        ).first()
        assert task is not None
        assert "ends today" in task.title
