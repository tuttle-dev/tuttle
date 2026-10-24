"""A project is settled by one final invoice at a time.

A second final invoice would bill the contract price again and take over the
deposits, so the first one's balance would jump back to the full price.
Cancelling the final invoice voids the settlement and allows a new one.
"""

import datetime
from decimal import Decimal

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.core.rpc_utils import dump
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.app.projects.intent import ProjectsIntent
from tuttle.model import Address, Client, Contract, Invoice, PaymentMilestone, Project, User
from tuttle.time import ContractType, Cycle

DATE = datetime.date(2026, 2, 1)


@pytest.fixture
def in_memory_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _contract(*percentages: str) -> Contract:
    return Contract(
        term_of_payment=14,
        title="Central Heating Overhaul",
        client=Client(name="Sam Lowry"),
        start_date=datetime.date(2026, 1, 10),
        type=ContractType.fixed_price,
        fixed_price=Decimal("10000"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        billing_cycle=Cycle.monthly,
        payment_milestones=[
            PaymentMilestone(title=f"Instalment {position + 1}", percentage=Decimal(pct), position=position)
            for position, pct in enumerate(percentages)
        ],
    )


def _project(contract: Contract) -> Project:
    return Project(
        title="Heating Overhaul",
        description="Ductwork",
        tag="#overhaul",
        contract=contract,
        start_date=datetime.date(2026, 1, 10),
    )


def _persist(engine, *percentages: str) -> tuple[int, list[int]]:
    """Persist a fixed-price project with one milestone per percentage."""
    with Session(engine) as session:
        # Rendering the PDF after creation reads the user's preferences.
        session.add(
            User(
                name="Harry Tuttle",
                subtitle="Heating Engineer",
                email="mail@tuttle.example",
                operating_country="Germany",
                address=Address(street="Main Street", number="450", postal_code="55555", city="Sao Paolo", country="Brazil"),
            )
        )
        project = _project(_contract(*percentages))
        session.add(project)
        session.commit()
        return project.id, [m.id for m in project.contract.payment_milestones]


def _ok(result):
    assert result.was_intent_successful, result.error_msg
    return result.data


def _finals(engine) -> list[int]:
    with Session(engine) as session:
        return list(session.exec(select(Invoice.id).where(Invoice.document_type == "final")).all())


class TestSecondFinalInvoice:
    def test_is_refused_and_names_the_final_invoice_to_cancel(self, in_memory_db):
        project_id, (first, _) = _persist(in_memory_db, "50", "50")
        intent = InvoicingIntent()
        _ok(intent.create_deposit(project_id, first, DATE))
        final = _ok(intent.create_final(project_id, DATE))

        result = intent.create_final(project_id, DATE)

        assert not result.was_intent_successful
        assert result.error_msg == (
            f"Final invoice {final.number} already settles this project. Cancel it to issue a new final invoice."
        )
        assert _finals(in_memory_db) == [final.id]

    def test_leaves_the_first_settlement_untouched(self, in_memory_db):
        project_id, (first, _) = _persist(in_memory_db, "50", "50")
        intent = InvoicingIntent()
        deposit = _ok(intent.create_deposit(project_id, first, DATE))
        final = _ok(intent.create_final(project_id, DATE))

        intent.create_final(project_id, DATE)

        settled = _ok(intent._invoicing_data_source.get_invoice_by_id(final.id))
        assert [d.id for d in settled.deposits] == [deposit.id]
        # 11,900 gross less the 5,950 deposit.
        assert settled.remaining_balance == Decimal("5950.00")

    def test_is_refused_on_a_contract_without_deposits(self, in_memory_db):
        project_id, _ = _persist(in_memory_db)
        intent = InvoicingIntent()
        final = _ok(intent.create_final(project_id, DATE))

        result = intent.create_final(project_id, DATE)

        assert not result.was_intent_successful
        assert f"Final invoice {final.number} already settles this project." in result.error_msg
        assert _finals(in_memory_db) == [final.id]

    def test_is_allowed_once_the_first_is_cancelled(self, in_memory_db):
        project_id, _ = _persist(in_memory_db)
        intent = InvoicingIntent()
        final = _ok(intent.create_final(project_id, DATE))
        _ok(intent.toggle_cancelled(final.id))

        replacement = _ok(intent.create_final(project_id, DATE))

        assert replacement.id != final.id
        assert _ok(ProjectsIntent().get_by_id(project_id)).final_invoice.id == replacement.id


class TestProjectIsSettled:
    @staticmethod
    def _with(*documents: str) -> Project:
        """A project with one invoice per document type, "cancelled final" for a cancelled one."""
        project = _project(_contract())
        project.invoices = [
            Invoice(
                number=f"2026-{position + 1:02d}",
                date=DATE,
                document_type=kind.removeprefix("cancelled "),
                cancelled=kind.startswith("cancelled "),
            )
            for position, kind in enumerate(documents)
        ]
        return project

    def test_a_final_invoice_settles_the_project(self):
        project = self._with("deposit", "final")
        assert project.is_settled
        assert project.final_invoice.number == "2026-02"

    def test_a_cancelled_final_invoice_does_not(self):
        project = self._with("deposit", "cancelled final")
        assert not project.is_settled
        assert project.final_invoice is None

    def test_deposits_alone_do_not(self):
        assert not self._with("deposit", "deposit").is_settled

    def test_the_project_list_tells_the_ui(self, in_memory_db):
        project_id, _ = _persist(in_memory_db)
        intent = InvoicingIntent()
        assert dump(_ok(ProjectsIntent().get_all()))[0]["is_settled"] is False

        _ok(intent.create_final(project_id, DATE))

        assert dump(_ok(ProjectsIntent().get_all()))[0]["is_settled"] is True
        # An invoice carries its project too, and must serialise without the project's invoices.
        assert [inv["project"] for inv in dump(_ok(intent.get_all()))] == [{"id": project_id, "title": "Heating Overhaul"}]
