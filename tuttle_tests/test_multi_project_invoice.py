"""One invoice billing several projects of one contract (#666), through the intent."""

import datetime
from decimal import Decimal

import pandas
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from tuttle.app.core.abstractions import SQLModelDataSourceMixin
from tuttle.app.invoicing.intent import InvoicingIntent
from tuttle.model import Address, Client, Contract, Invoice, Project
from tuttle.time import ContractType, Cycle, TimeUnit


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(SQLModelDataSourceMixin, "create_session", lambda self: Session(engine))
    return engine


def _contract(title, client, **kw) -> Contract:
    fields = dict(
        title=title,
        client=client,
        start_date=datetime.date(2026, 1, 1),
        rate=Decimal("500"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=TimeUnit.day,
        units_per_workday=8,
        billing_cycle=Cycle.monthly,
        term_of_payment=14,
    )
    fields.update(kw)
    return Contract(**fields)


def _project(contract, tag, rate=None) -> Project:
    return Project(
        title=f"Project {tag}",
        description="",
        tag=tag,
        start_date=datetime.date(2026, 1, 1),
        contract=contract,
        rate=rate,
    )


@pytest.fixture
def setup(db):
    """Projects #a, #b (own rate 650) on one contract, #c on another, #fp fixed-price."""
    client = Client(name="Central Services", address=Address(street="A", number="1", postal_code="1", city="X", country="Germany"))
    retainer = _contract("Retainer", client)
    other = _contract("Other", client)
    fixed = _contract("Fixed", client, type=ContractType.fixed_price, fixed_price=Decimal("1000"), rate=None)
    projects = [
        _project(retainer, "#a"),
        _project(retainer, "#b", Decimal("650")),
        _project(retainer, "#idle"),
        _project(other, "#c"),
        _project(fixed, "#fp"),
        _project(fixed, "#fp2"),
    ]
    with Session(db) as session:
        session.add_all(projects)
        session.commit()
        ids = {p.tag: p.id for p in projects}
    return ids


def _intent(monkeypatch, tags=("#a", "#b", "#c", "#fp", "#fp2")) -> InvoicingIntent:
    begin = pandas.to_datetime(["2026-03-02 09:00"] * len(tags))
    df = pandas.DataFrame(
        {
            "begin": begin,
            "end": begin + pandas.Timedelta(hours=8),
            "title": ["Work"] * len(tags),
            "tag": list(tags),
            "description": [""] * len(tags),
            "all_day": [False] * len(tags),
        }
    )
    df["duration"] = df["end"] - df["begin"]
    intent = InvoicingIntent()
    monkeypatch.setattr(intent._timetracking_data_source, "get_data_frame", lambda: df.set_index("begin"))
    return intent


def _create(intent, ids, primary, others=(), **kw):
    return intent.create(
        project_id=ids[primary],
        project_ids=[ids[t] for t in others],
        invoice_date="2026-04-01",
        from_date="2026-03-01",
        to_date="2026-03-31",
        render=False,
        **kw,
    )


def _saved_invoice(db) -> Invoice:
    with Session(db) as session:
        invoice = session.exec(select(Invoice)).one()
        _ = [(i.project, i.description) for i in invoice.items], invoice.timesheets, invoice.project
        return invoice


def test_create_bills_two_projects(db, setup, monkeypatch):
    result = _create(_intent(monkeypatch), setup, "#a", ["#b"])
    assert result.was_intent_successful, result.error_msg
    invoice = _saved_invoice(db)
    assert [(i.project_id, i.unit_price) for i in invoice.items] == [(setup["#a"], 500), (setup["#b"], 650)]
    assert len(invoice.timesheets) == 2
    assert invoice.contract_id is not None  # one contract object across projects keeps the link
    assert invoice.project_id is None
    assert invoice.project_titles == "Project #a, Project #b"


def test_create_rejects_other_contract(db, setup, monkeypatch):
    result = _create(_intent(monkeypatch), setup, "#a", ["#c"])
    assert not result.was_intent_successful
    assert result.error_msg == "All projects on one invoice must belong to the same time-based contract."
    with Session(db) as session:
        assert session.exec(select(Invoice)).all() == []


def test_create_rejects_fixed_price_multi(db, setup, monkeypatch):
    result = _create(_intent(monkeypatch), setup, "#fp", ["#fp2"])
    assert result.error_msg == "All projects on one invoice must belong to the same time-based contract."


def test_project_without_hours_is_skipped(db, setup, monkeypatch):
    result = _create(_intent(monkeypatch), setup, "#a", ["#idle"])
    assert result.was_intent_successful, result.error_msg
    invoice = _saved_invoice(db)
    assert [i.project_id for i in invoice.items] == [setup["#a"]]
    assert invoice.project_id == setup["#a"]


def test_manual_lines_carry_their_project(db, setup, monkeypatch):
    items = [
        {"description": "Ducts", "quantity": 2, "unit": "day", "unit_price": 500},
        {"description": "Review", "quantity": 1, "unit": "day", "unit_price": 650, "project_id": setup["#b"]},
    ]
    result = _create(_intent(monkeypatch), setup, "#a", manual_items=items)
    assert result.was_intent_successful, result.error_msg
    invoice = _saved_invoice(db)
    assert [i.project_id for i in invoice.items] == [setup["#a"], setup["#b"]]
    assert invoice.project_id is None


def test_manual_quantity_uses_project_rate(db, setup, monkeypatch):
    result = _create(_intent(monkeypatch), setup, "#b", manual_quantity=2)
    assert result.was_intent_successful, result.error_msg
    assert _saved_invoice(db).items[0].unit_price == 650


def test_set_item_projects_reassigns_and_derives(db, setup, monkeypatch):
    intent = _intent(monkeypatch)
    _create(intent, setup, "#a", ["#b"])
    invoice = _saved_invoice(db)
    first, second = invoice.items
    result = intent.set_item_projects(invoice.id, {str(second.id): setup["#a"]})
    assert result.was_intent_successful, result.error_msg
    invoice = _saved_invoice(db)
    assert [i.project_id for i in invoice.items] == [setup["#a"], setup["#a"]]
    assert invoice.project_id == setup["#a"]

    intent.set_item_projects(invoice.id, {str(first.id): setup["#b"]})
    assert _saved_invoice(db).project_id is None


def test_set_item_projects_rejects_foreign_project(db, setup, monkeypatch):
    intent = _intent(monkeypatch)
    _create(intent, setup, "#a")
    invoice = _saved_invoice(db)
    result = intent.set_item_projects(invoice.id, {str(invoice.items[0].id): setup["#c"]})
    assert not result.was_intent_successful
    assert result.error_msg == "Project does not belong to this invoice's contract."
    assert _saved_invoice(db).items[0].project_id == setup["#a"]


def test_timesheet_paths_list_every_project(db, setup, monkeypatch, tmp_path):
    intent = _intent(monkeypatch)
    _create(intent, setup, "#a", ["#b"])
    invoice = _saved_invoice(db)
    assert invoice.timesheet_pdf_paths == []  # nothing rendered yet



def test_email_names_every_project(db, setup, monkeypatch):
    from tuttle import invoicing

    _create(_intent(monkeypatch), setup, "#a", ["#b"])
    invoice = _saved_invoice(db)
    with Session(db) as session:
        invoice = session.get(Invoice, invoice.id)
        _ = invoice.contract.client.invoicing_contact
        client = invoice.contract.client
    from tuttle.model import Contact, User

    invoice.contract.client.invoicing_contact = Contact(first_name="Sam", last_name="Lowry", email="sam@example.com")
    email = invoicing.generate_invoice_email(invoice, User(name="Harry Tuttle", email="harry@example.com"))
    assert "Project #a, Project #b" in email["body"]


def test_render_timesheets_renders_every_project(db, setup, monkeypatch):
    intent = _intent(monkeypatch)
    _create(intent, setup, "#a", ["#b"])
    rendered = []
    monkeypatch.setattr("tuttle.rendering.render_timesheet", lambda **kw: rendered.append(kw["timesheet"].project.tag))
    monkeypatch.setattr(intent._user_data_source, "get_user", lambda: None)
    result = intent.render_timesheet_for_invoice(_saved_invoice(db).id)
    assert result.was_intent_successful, result.error_msg
    assert rendered == ["#a", "#b"]


def test_project_save_stores_rate(db, setup):
    from tuttle.app.projects.intent import ProjectsIntent

    with Session(db) as session:
        contract_id = session.get(Project, setup["#a"]).contract_id
    payload = {"id": setup["#a"], "title": "Project #a", "tag": "#a", "description": "", "start_date": "2026-01-01",
               "contract_id": contract_id, "rate": 720}
    result = ProjectsIntent().save_from_dict(payload)
    assert result.was_intent_successful, result.error_msg
    with Session(db) as session:
        assert session.get(Project, setup["#a"]).effective_rate == Decimal("720")
    payload["rate"] = None
    ProjectsIntent().save_from_dict(payload)
    with Session(db) as session:
        assert session.get(Project, setup["#a"]).rate is None
