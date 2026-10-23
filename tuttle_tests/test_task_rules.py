"""Tests for task rules (tuttle/app/tasks/rules.py) and the tasks the generator makes from them."""

import datetime
from decimal import Decimal

import pytest
import sqlmodel
from sqlmodel import select

from tuttle.app.tasks.generator import generate_tasks
from tuttle.app.tasks.rules import (
    EVENTS,
    RECORDS,
    add_months,
    evaluate,
    occurrences,
    period_before,
    render,
    rule_options,
    shift,
    start_watching,
    validate_rule,
)
from tuttle.model import (
    Client,
    Contract,
    FinancialGoal,
    Invoice,
    InvoiceItem,
    Project,
    Task,
    TaskRule,
    TaskRuleNotice,
)
from tuttle.time import Cycle, TimeUnit

# Statuses (an invoice being overdue, a project's board stage) are read off the
# real calendar, so the tests build their records around the real today.
TODAY = datetime.date.today()


def days(n: int) -> datetime.date:
    return TODAY + datetime.timedelta(days=n)


def made(n_days_ago: int) -> datetime.datetime:
    return datetime.datetime.combine(days(-n_days_ago), datetime.time(9))


@pytest.fixture
def session():
    engine = sqlmodel.create_engine("sqlite://", echo=False)
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def client(session, name="Acme"):
    c = Client(name=name)
    session.add(c)
    session.commit()
    return c


def contract(session, cl, title="Retainer", start=None, end=None, cycle=Cycle.monthly, completed=False, signed=None):
    c = Contract(
        title=title,
        client=cl,
        rate=Decimal("100"),
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        unit=TimeUnit.hour,
        units_per_workday=8,
        term_of_payment=14,
        billing_cycle=cycle,
        start_date=start or days(-100),
        end_date=end,
        is_completed=completed,
        signature_date=signed,
    )
    session.add(c)
    session.commit()
    return c


def project(session, ct, title="Build", start=None, end=None, stage=None):
    p = Project(
        title=title,
        tag="#" + title.lower().replace(" ", ""),
        description=title,
        contract=ct,
        start_date=start or days(-50),
        end_date=end,
        stage=stage,
    )
    session.add(p)
    session.commit()
    return p


def invoice(session, ct, number="2026-001", date=None, sent=True, paid=False, cancelled=False, sent_date=None):
    """An invoice dated ``date``, due 14 days later (the contract's terms)."""
    inv = Invoice(
        number=number,
        date=date or days(-20),
        contract=ct,
        sent=sent,
        sent_date=sent_date if sent_date is not None else (date or days(-20)) if sent else None,
        paid=paid,
        cancelled=cancelled,
        items=[InvoiceItem(quantity=1, unit="h", unit_price=Decimal("100"), description="Work", VAT_rate=Decimal("0.19"))],
    )
    session.add(inv)
    session.commit()
    return inv


def rule(session, created=None, **fields):
    """A rule saved the way the composer saves it: validated, and watching from the day it's made."""
    fields.setdefault("title", "Task about {contract}")
    fields.setdefault("kind", "event")
    r = TaskRule(created_at=created or made(365), **fields)
    validate_rule(r)
    session.add(r)
    session.flush()
    start_watching(session, r, r.created_at.date())
    session.commit()
    return r


def tasks_of(session, r, status=None):
    query = select(Task).where(Task.rule_id == r.id)
    if status:
        query = query.where(Task.status == status)
    return session.exec(query.order_by(Task.due_date)).all()


# ---------------------------------------------------------------------------
# Dates and text
# ---------------------------------------------------------------------------


class TestDates:
    def test_add_months_keeps_within_the_month(self):
        assert add_months(datetime.date(2026, 1, 31), 1) == datetime.date(2026, 2, 28)
        assert add_months(datetime.date(2028, 1, 31), 1) == datetime.date(2028, 2, 29)
        assert add_months(datetime.date(2026, 11, 15), 3) == datetime.date(2027, 2, 15)
        assert add_months(datetime.date(2026, 3, 31), -1) == datetime.date(2026, 2, 28)

    def test_add_months_returns_to_the_anchor_day(self):
        assert add_months(datetime.date(2026, 2, 28), 1, day=31) == datetime.date(2026, 3, 31)

    def test_shift(self):
        d = datetime.date(2026, 10, 15)
        assert shift(d, -30, "day") == datetime.date(2026, 9, 15)
        assert shift(d, 2, "week") == datetime.date(2026, 10, 29)
        assert shift(d, -1, "month") == datetime.date(2026, 9, 15)


class TestRender:
    def test_fills_placeholders(self):
        assert render("{contract} ends on {date}", {"contract": "Retainer", "date": "Nov 6, 2026"}) == (
            "Retainer ends on Nov 6, 2026"
        )

    def test_keeps_unknown_placeholders(self):
        assert render("Send {invoice} for {period}", {"invoice": "2026-001"}) == "Send 2026-001 for {period}"

    @pytest.mark.parametrize("template", ["Pay { now", "Odd {0} index", "{contract.title}", "close } brace"])
    def test_keeps_text_that_is_not_a_template(self, template):
        assert render(template, {"contract": "Retainer"}) == template

    def test_none_and_empty(self):
        assert render(None, {}) is None
        assert render("", {}) == ""


class TestSchedules:
    def _rule(self, start, unit=None, every=1):
        return TaskRule(title="t", kind="date", start_date=start, unit=unit, every=every)

    def test_once(self):
        r = self._rule(datetime.date(2026, 12, 1))
        assert list(occurrences(r, datetime.date(2027, 12, 31))) == [datetime.date(2026, 12, 1)]
        assert list(occurrences(r, datetime.date(2026, 11, 30))) == []

    def test_every_two_weeks(self):
        r = self._rule(datetime.date(2026, 10, 5), "week", 2)
        assert list(occurrences(r, datetime.date(2026, 11, 3))) == [
            datetime.date(2026, 10, 5),
            datetime.date(2026, 10, 19),
            datetime.date(2026, 11, 2),
        ]

    def test_monthly_from_the_31st_keeps_to_month_ends(self):
        r = self._rule(datetime.date(2026, 1, 31), "month")
        assert list(occurrences(r, datetime.date(2026, 4, 30))) == [
            datetime.date(2026, 1, 31),
            datetime.date(2026, 2, 28),
            datetime.date(2026, 3, 31),
            datetime.date(2026, 4, 30),
        ]

    def test_quarterly(self):
        r = self._rule(datetime.date(2026, 1, 10), "month", 3)
        assert list(occurrences(r, datetime.date(2026, 12, 31))) == [
            datetime.date(2026, 1, 10),
            datetime.date(2026, 4, 10),
            datetime.date(2026, 7, 10),
            datetime.date(2026, 10, 10),
        ]

    @pytest.mark.parametrize(
        "unit, every, occurrence, expected",
        [
            ("month", 1, datetime.date(2026, 11, 1), "October 2026"),
            ("month", 1, datetime.date(2027, 1, 1), "December 2026"),
            ("month", 3, datetime.date(2027, 1, 10), "Q4 2026"),
            ("month", 3, datetime.date(2026, 10, 10), "Q3 2026"),
            ("month", 6, datetime.date(2026, 7, 1), "H1 2026"),
            ("month", 12, datetime.date(2027, 5, 31), "2026"),
            ("week", 1, datetime.date(2026, 10, 15), "the week of Oct 5, 2026"),
            (None, 1, datetime.date(2026, 12, 1), "November 2026"),
        ],
    )
    def test_period_before(self, unit, every, occurrence, expected):
        assert period_before(occurrence, self._rule(occurrence, unit, every)) == expected


# ---------------------------------------------------------------------------
# The catalog
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_events_come_from_each_records_dates_and_statuses(self):
        for rk, record in RECORDS.items():
            for dk in record.dates:
                assert f"{rk}.{dk}" in EVENTS
            for status in record.states:
                assert f"{rk}={status}" in EVENTS
        assert len(EVENTS) == sum(len(r.dates) + len(r.states) for r in RECORDS.values())

    def test_statuses_a_rule_follows_are_ones_tuttle_shows(self):
        assert set(RECORDS["project"].states) <= {"Lead", "Offer", "Upcoming", "Active", "Completed"}
        assert set(RECORDS["contract"].states) <= {"Lead", "Offer", "Upcoming", "Active", "Completed"}
        assert set(RECORDS["invoice"].states) <= {"draft", "sent", "overdue", "paid", "cancelled"}

    def test_only_anticipated_dates_allow_a_task_before(self):
        after_only = {k for k, e in EVENTS.items() if e.after_only}
        assert {"invoice.created", "invoice.sent"} <= after_only
        assert all(k in after_only for k, e in EVENTS.items() if e.is_state)
        assert "contract.end" not in after_only and "invoice.due" not in after_only

    def test_every_event_has_a_default_title_using_its_records_placeholders(self):
        for e in EVENTS.values():
            placeholders = set(RECORDS[e.record].placeholders)
            for title in filter(None, e.titles):
                used = {part.split("}")[0] for part in title.split("{")[1:]}
                assert used <= placeholders, (e.key, used - placeholders)

    def test_options_for_the_composer(self):
        options = rule_options()
        records = {r["key"]: r for r in options["records"]}
        assert set(records) == {"contract", "project", "invoice", "goal"}
        offer = next(e for e in records["project"]["events"] if e["key"] == "project=Offer")
        assert offer == {
            "key": "project=Offer",
            "label": "becomes an offer",
            "state": True,
            "final": False,
            "after_only": True,
            "title_before": None,
            "title_after": "Follow up on the offer for {project}",
        }


class TestValidation:
    @pytest.mark.parametrize(
        "fields, message",
        [
            ({"title": "  ", "kind": "date", "start_date": TODAY}, "Give the task a title."),
            ({"title": "t", "kind": "date"}, "Choose the date of the task."),
            ({"title": "t", "kind": "date", "start_date": TODAY, "unit": "fortnight"}, "Choose how often"),
            ({"title": "t", "kind": "date", "start_date": TODAY, "unit": "month", "every": 0}, "at least once"),
            ({"title": "t", "kind": "event"}, "Choose what the task follows"),
            ({"title": "t", "kind": "event", "event": "contract.vanishes"}, "Choose what the task follows"),
            ({"title": "t", "kind": "event", "event": "contract.end", "offset": -3}, "as 0 or more"),
            ({"title": "t", "kind": "event", "event": "contract.end", "offset_unit": "year"}, "days, weeks or months"),
            (
                {"title": "t", "kind": "event", "event": "invoice.sent", "offset": 2, "before": True},
                "only once it has happened",
            ),
            (
                {"title": "t", "kind": "event", "event": "project=Offer", "offset": 2, "before": True},
                "only once it has happened",
            ),
            ({"title": "t", "kind": "sometimes"}, "on a date or when something happens"),
        ],
    )
    def test_rejects_with_a_message_for_the_user(self, fields, message):
        with pytest.raises(ValueError, match=message):
            validate_rule(TaskRule(**fields))

    def test_tidies_fields_the_kind_does_not_use(self):
        r = TaskRule(title=" Renew ", note="  ", kind="date", start_date=TODAY, event="contract.end", client_id=3)
        validate_rule(r)
        assert (r.title, r.note, r.event, r.client_id) == ("Renew", None, None, None)
        r = TaskRule(
            title="t", kind="event", event="goal.target", client_id=3, offset=0, before=True, start_date=TODAY, unit="month"
        )
        validate_rule(r)
        assert (r.client_id, r.before, r.start_date, r.unit) == (None, False, None, None)


# ---------------------------------------------------------------------------
# Rules on a date
# ---------------------------------------------------------------------------


class TestDateRules:
    def test_monthly_task_for_the_latest_day_only(self, session):
        # Made four months ago on the 1st: three or four 1sts have passed, one task.
        start = add_months(TODAY, -4, 1)
        r = rule(
            session,
            created=made((TODAY - start).days),
            title="Send invoices for {period}",
            kind="date",
            start_date=start,
            unit="month",
        )
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        latest = TODAY.replace(day=1)
        assert task.due_date == latest
        assert task.title == f"Send invoices for {period_before(latest, r)}"
        assert task.key == f"rule:{r.id}:{latest.isoformat()}"

    def test_next_month_adds_a_task_and_keeps_the_last(self, session):
        r = rule(
            session,
            created=made(40),
            title="Send invoices for {period}",
            kind="date",
            start_date=add_months(TODAY, -1, 1),
            unit="month",
        )
        generate_tasks(session, TODAY)
        generate_tasks(session, add_months(TODAY, 1, 1))
        assert [t.status for t in tasks_of(session, r)] == ["pending", "pending"]

    def test_days_before_the_rule_was_made_are_left_alone(self, session):
        r = rule(session, created=made(0), title="Call the tax office", kind="date", start_date=days(-10))
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []
        assert evaluate(r, session, TODAY).next is None

    def test_once_today_and_once_later(self, session):
        today_rule = rule(session, created=made(0), title="Today's thing", kind="date", start_date=TODAY)
        later_rule = rule(session, created=made(0), title="Renew insurance", kind="date", start_date=days(45))
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, today_rule)] == ["Today's thing"]
        assert tasks_of(session, later_rule) == []
        assert evaluate(later_rule, session, TODAY).next.trigger == days(45)
        generate_tasks(session, days(45))
        assert [t.due_date for t in tasks_of(session, later_rule)] == [days(45)]

    def test_idempotent_and_done_stays_done(self, session):
        r = rule(session, created=made(0), title="Today's thing", kind="date", start_date=TODAY)
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        task.status = "done"
        session.add(task)
        session.commit()
        generate_tasks(session, TODAY)
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["done"]

    def test_paused_rule_makes_nothing(self, session):
        r = rule(session, created=made(0), title="Today's thing", kind="date", start_date=TODAY, paused=True)
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []

    def test_note_is_rendered_too(self, session):
        r = rule(
            session,
            created=made(0),
            title="VAT",
            note="For {period}, by {date}",
            kind="date",
            start_date=TODAY,
            unit="month",
            every=3,
        )
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert task.description == f"For {period_before(TODAY, r)}, by {TODAY:%b} {TODAY.day}, {TODAY.year}"


# ---------------------------------------------------------------------------
# Rules around a date on a record
# ---------------------------------------------------------------------------


class TestContractEnd:
    def _rule(self, session, **kw):
        return rule(session, title="{contract} ends on {date}", event="contract.end", offset=30, before=True, **kw)

    def test_heads_up_within_the_window(self, session):
        ct = contract(session, client(session), title="Retainer", end=days(10))
        r = self._rule(session)
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert task.title == f"Retainer ends on {days(10):%b} {days(10).day}, {days(10).year}"
        assert (task.due_date, task.subject_type, task.subject_id) == (days(10), "contract", ct.id)
        assert task.key == f"rule:{r.id}:contract:{ct.id}"

    def test_outside_the_window_it_waits(self, session):
        contract(session, client(session), end=days(40))
        r = self._rule(session)
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []
        assert evaluate(r, session, TODAY).next.trigger == days(10)

    @pytest.mark.parametrize(
        "kw",
        [{"end": days(-5)}, {"end": days(10), "completed": True}, {"end": None}],
        ids=["ended already", "completed", "open-ended"],
    )
    def test_no_heads_up(self, session, kw):
        contract(session, client(session), **kw)
        r = self._rule(session)
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []

    def test_closes_when_the_contract_is_completed(self, session):
        ct = contract(session, client(session), end=days(10))
        r = self._rule(session)
        generate_tasks(session, TODAY)
        ct.is_completed = True
        session.add(ct)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["done"]

    def test_a_moved_end_date_moves_the_task(self, session):
        ct = contract(session, client(session), title="Retainer", end=days(10))
        r = self._rule(session)
        generate_tasks(session, TODAY)
        ct.end_date = days(20)
        session.add(ct)
        session.commit()
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert task.due_date == days(20)
        assert task.title.endswith(f"{days(20).day}, {days(20).year}")

    def test_an_extended_contract_drops_the_task_and_warns_again_later(self, session):
        ct = contract(session, client(session), end=days(10))
        r = self._rule(session)
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        task.status = "done"
        session.add(task)
        ct.end_date = days(200)
        session.add(ct)
        session.commit()
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []
        generate_tasks(session, days(175))
        assert [(t.status, t.due_date) for t in tasks_of(session, r)] == [("pending", days(200))]

    def test_a_task_from_before_due_dates_existed_is_adopted(self, session):
        """Tasks moved over by the migration have no due date yet; they keep their status."""
        ct = contract(session, client(session), end=days(10))
        r = self._rule(session)
        session.add(
            Task(
                key=f"rule:{r.id}:contract:{ct.id}",
                title="old",
                status="dismissed",
                rule_id=r.id,
                subject_type="contract",
                subject_id=ct.id,
            )
        )
        session.commit()
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert (task.status, task.due_date, task.title) == ("dismissed", days(10), "old")

    def test_a_deleted_contract_takes_its_pending_task(self, session):
        ct = contract(session, client(session), end=days(10))
        r = self._rule(session)
        generate_tasks(session, TODAY)
        session.delete(ct)
        session.commit()
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []

    def test_renaming_the_contract_or_the_rule_updates_the_pending_title(self, session):
        ct = contract(session, client(session), title="Retainer", end=days(10))
        r = self._rule(session)
        generate_tasks(session, TODAY)
        ct.title = "Big Retainer"
        r.title = "Talk about extending {contract}"
        session.add_all([ct, r])
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["Talk about extending Big Retainer"]


class TestFollowUps:
    """After a contract or project date, a task is a follow-up: it counts only dates after the rule was made."""

    def test_dates_before_the_rule_was_made_are_left_alone(self, session):
        contract(session, client(session), start=days(-10))
        r = rule(session, created=made(0), event="contract.start", offset=1, offset_unit="week")
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []

    def test_a_later_date_gets_its_follow_up(self, session):
        ct = contract(session, client(session), start=days(3))
        r = rule(session, created=made(0), event="contract.start", offset=1, offset_unit="week")
        assert evaluate(r, session, TODAY).next.trigger == days(10)
        generate_tasks(session, days(10))
        assert [t.subject_id for t in tasks_of(session, r)] == [ct.id]

    def test_a_follow_up_stays_when_the_contract_is_completed(self, session):
        ct = contract(session, client(session), start=days(-200), end=days(-10))
        r = rule(session, created=made(30), title="Ask for a testimonial", event="contract.end", offset=1, offset_unit="week")
        generate_tasks(session, TODAY)
        ct.is_completed = True
        session.add(ct)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["pending"]

    def test_project_end_heads_up_closes_on_completion(self, session):
        p = project(session, contract(session, client(session)), end=days(5))
        r = rule(session, title="{project} ends", event="project.end", offset=1, offset_unit="week", before=True)
        generate_tasks(session, TODAY)
        assert len(tasks_of(session, r, "pending")) == 1
        p.is_completed = True
        session.add(p)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["done"]


class TestInvoices:
    def _overdue_rule(self, session, **kw):
        return rule(
            session,
            title="Invoice {invoice} is overdue — send a reminder",
            note="It was due on {date}.",
            event="invoice.due",
            offset=1,
            **kw,
        )

    def test_overdue_invoice_gets_a_reminder_task(self, session):
        inv = invoice(session, contract(session, client(session)), number="2026-007", date=days(-30))
        r = self._overdue_rule(session)
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert task.title == "Invoice 2026-007 is overdue — send a reminder"
        assert task.description == f"It was due on {inv.due_date:%b} {inv.due_date.day}, {inv.due_date.year}."
        assert (task.subject_type, task.subject_id, task.due_date) == ("invoice", inv.id, inv.due_date)

    def test_open_invoices_from_before_the_rule_are_caught_up_on(self, session):
        invoice(session, contract(session, client(session)), date=days(-400))
        r = self._overdue_rule(session, created=made(0))
        generate_tasks(session, TODAY)
        assert len(tasks_of(session, r)) == 1

    @pytest.mark.parametrize("kw", [{"sent": False}, {"paid": True}, {"cancelled": True}], ids=["draft", "paid", "cancelled"])
    def test_no_task_for_a_closed_or_unsent_invoice(self, session, kw):
        invoice(session, contract(session, client(session)), date=days(-30), **kw)
        r = self._overdue_rule(session)
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []

    def test_payment_closes_the_task(self, session):
        inv = invoice(session, contract(session, client(session)), date=days(-30))
        r = self._overdue_rule(session)
        generate_tasks(session, TODAY)
        inv.paid = True
        session.add(inv)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["done"]

    def test_a_reminder_takes_over_from_the_invoice(self, session):
        ct = contract(session, client(session))
        inv = invoice(session, ct, number="2026-007", date=days(-60))
        r = self._overdue_rule(session)
        generate_tasks(session, TODAY)
        reminder = Invoice(
            number="2026-007-M1",
            date=days(-20),
            contract=ct,
            document_type="reminder",
            reminder_for_id=inv.id,
            reminder_level=1,
            sent=True,
            sent_date=days(-20),
            items=[],
        )
        session.add(reminder)
        session.commit()
        generate_tasks(session, TODAY)
        by_subject = {t.subject_id: t for t in tasks_of(session, r)}
        assert by_subject[inv.id].status == "done"
        assert by_subject[reminder.id].status == "pending"
        assert by_subject[reminder.id].title == "Invoice 2026-007-M1 is overdue — send a reminder"

    def test_heads_up_before_it_is_due(self, session):
        ct = contract(session, client(session), title="Retainer")
        invoice(session, ct, number="A", date=days(-12))  # due in 2 days
        invoice(session, ct, number="B", date=days(-4))  # due in 10 days
        r = rule(session, title="{invoice} due {date}", event="invoice.due", offset=3, before=True)
        generate_tasks(session, TODAY)
        assert [t.title.split()[0] for t in tasks_of(session, r)] == ["A"]
        assert evaluate(r, session, TODAY).next.trigger == days(7)

    def test_unsent_invoice_reminder_closes_once_sent(self, session):
        inv = invoice(session, contract(session, client(session)), date=days(-5), sent=False)
        r = rule(session, title="Send invoice {invoice} to {client}", event="invoice.created", offset=3)
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert task.title == "Send invoice 2026-001 to Acme"
        inv.sent, inv.sent_date = True, TODAY
        session.add(inv)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["done"]

    def test_follow_up_after_sending(self, session):
        ct = contract(session, client(session))
        invoice(session, ct, number="A", date=days(-10), sent_date=days(-10))
        invoice(session, ct, number="B", date=days(-3), sent_date=days(-3))
        r = rule(session, title="Check {invoice}", event="invoice.sent", offset=1, offset_unit="week")
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["Check A"]


class TestBillingPeriods:
    def test_the_latest_period_end_gets_a_task(self, session):
        ct = contract(session, client(session), title="Retainer", start=add_months(TODAY, -6, 1))
        r = rule(
            session, created=made(45), title="Invoice {contract} for the period ending {date}", event="contract.period_end"
        )
        generate_tasks(session, TODAY)
        last_end = TODAY.replace(day=1) - datetime.timedelta(days=1)
        (task,) = tasks_of(session, r)
        assert task.due_date == last_end
        assert task.key == f"rule:{r.id}:contract:{ct.id}:{last_end.isoformat()}"
        next_end = add_months(TODAY.replace(day=1), 1) - datetime.timedelta(days=1)
        assert evaluate(r, session, TODAY).next.trigger == next_end

    def test_each_period_keeps_its_own_task(self, session):
        contract(session, client(session), start=add_months(TODAY, -6, 1))
        r = rule(session, created=made(45), event="contract.period_end")
        generate_tasks(session, TODAY)
        generate_tasks(session, add_months(TODAY, 1))
        assert len(tasks_of(session, r, "pending")) == 2

    def test_the_last_period_ends_with_the_contract(self, session):
        ct = contract(session, client(session), start=add_months(TODAY, -6, 1), end=days(5), cycle=Cycle.monthly)
        r = rule(session, created=made(0), event="contract.period_end")
        generate_tasks(session, days(5))
        assert [t.due_date for t in tasks_of(session, r)] == [ct.end_date]
        assert evaluate(r, session, days(6)).next is None

    def test_weekly_cycle(self, session):
        contract(session, client(session), start=days(-20), cycle=Cycle.weekly)
        r = rule(session, created=made(30), event="contract.period_end")
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert task.due_date == days(-20) + datetime.timedelta(days=20)

    @pytest.mark.parametrize("cycle", [Cycle.hourly, Cycle.daily])
    def test_no_periods_for_hourly_or_daily_billing(self, session, cycle):
        contract(session, client(session), start=days(-20), cycle=cycle)
        r = rule(session, created=made(30), event="contract.period_end")
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []


class TestScopeAndGoals:
    def test_only_the_rules_client(self, session):
        acme, umbrella = client(session, "Acme"), client(session, "Umbrella")
        contract(session, acme, title="A", end=days(5))
        contract(session, umbrella, title="U", end=days(5))
        r = rule(
            session,
            title="{contract} for {client}",
            event="contract.end",
            offset=1,
            offset_unit="week",
            before=True,
            client_id=umbrella.id,
        )
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["U for Umbrella"]

    def test_a_task_out_of_a_narrowed_scope_goes(self, session):
        acme, umbrella = client(session, "Acme"), client(session, "Umbrella")
        contract(session, acme, title="A", end=days(5))
        r = rule(session, event="contract.end", offset=1, offset_unit="week", before=True)
        generate_tasks(session, TODAY)
        assert len(tasks_of(session, r)) == 1
        r.client_id = umbrella.id
        session.add(r)
        session.commit()
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []

    def test_goal_date(self, session):
        goal = FinancialGoal(title="Van fund", target_amount=Decimal("1000"), target_date=days(20))
        session.add(goal)
        session.commit()
        r = rule(session, title="{goal} is due on {date}", event="goal.target", offset=1, offset_unit="month", before=True)
        generate_tasks(session, TODAY)
        (task,) = tasks_of(session, r)
        assert task.title.startswith("Van fund is due on")
        goal.is_reached = True
        session.add(goal)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["done"]

    def test_a_rule_tuttle_does_not_know_is_left_alone(self, session):
        r = TaskRule(title="From a newer Tuttle", kind="event", event="invoice.disputed", created_at=made(1))
        session.add(r)
        session.commit()
        session.add(Task(key=f"rule:{r.id}:invoice:1", title="kept", rule_id=r.id, subject_type="invoice", subject_id=1))
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["kept"]


# ---------------------------------------------------------------------------
# Rules on status changes
# ---------------------------------------------------------------------------


class TestStatusChanges:
    def _offer_rule(self, session, offset=1, **kw):
        return rule(
            session,
            created=made(0),
            title="Follow up on the offer for {project}",
            event="project=Offer",
            offset=offset,
            offset_unit="week",
            **kw,
        )

    def test_offers_already_out_count(self, session):
        """An offer is something to act on: one already out when the rule is made gets its follow-up too."""
        project(session, contract(session, client(session)), title="Old offer", stage="Offer")
        r = self._offer_rule(session, offset=0)
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["Follow up on the offer for Old offer"]

    def test_projects_completed_before_the_rule_get_no_task(self, session):
        """Completed is where projects end up: only ones completed from the day the rule is made count."""
        project(session, contract(session, client(session)), title="Old job", stage="Completed")
        r = rule(session, created=made(0), title="{project}", event="project=Completed")
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []
        assert session.exec(select(TaskRuleNotice).where(TaskRuleNotice.rule_id == r.id)).one().already

    def test_a_new_offer_is_noticed_and_followed_up(self, session):
        r = self._offer_rule(session)
        p = project(session, contract(session, client(session)), title="Underfloor Heating", stage="Offer")
        generate_tasks(session, TODAY)
        assert tasks_of(session, r) == []
        notice = session.exec(select(TaskRuleNotice).where(TaskRuleNotice.rule_id == r.id)).one()
        assert (notice.subject_id, notice.noticed_on, notice.already) == (p.id, TODAY, False)
        generate_tasks(session, days(7))
        (task,) = tasks_of(session, r)
        assert task.title == "Follow up on the offer for Underfloor Heating"
        assert (task.due_date, task.key) == (TODAY, f"rule:{r.id}:project:{p.id}:{TODAY.isoformat()}")

    def test_as_soon_as(self, session):
        r = self._offer_rule(session, offset=0)
        project(session, contract(session, client(session)), stage="Offer")
        generate_tasks(session, TODAY)
        assert len(tasks_of(session, r, "pending")) == 1

    def test_an_offer_won_before_the_follow_up_gets_none(self, session):
        r = self._offer_rule(session)
        p = project(session, contract(session, client(session)), stage="Offer")
        generate_tasks(session, TODAY)
        p.stage = "Upcoming"
        session.add(p)
        session.commit()
        generate_tasks(session, days(1))
        generate_tasks(session, days(8))
        assert tasks_of(session, r) == []
        assert session.exec(select(TaskRuleNotice).where(TaskRuleNotice.rule_id == r.id)).all() == []

    def test_an_offer_won_after_the_follow_up_closes_it(self, session):
        r = self._offer_rule(session, offset=0)
        p = project(session, contract(session, client(session)), stage="Offer")
        generate_tasks(session, TODAY)
        p.stage = "Upcoming"
        session.add(p)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.status for t in tasks_of(session, r)] == ["done"]

    def test_an_offer_made_again_is_followed_up_again(self, session):
        r = self._offer_rule(session, offset=0)
        p = project(session, contract(session, client(session)), stage="Offer")
        generate_tasks(session, days(-3))
        p.stage = "Lead"
        session.add(p)
        session.commit()
        generate_tasks(session, days(-2))
        p.stage = "Offer"
        session.add(p)
        session.commit()
        generate_tasks(session, TODAY)
        assert [(t.status, t.due_date) for t in tasks_of(session, r)] == [("done", days(-3)), ("pending", TODAY)]

    def test_payment_thank_you(self, session):
        inv = invoice(session, contract(session, client(session, "Umbrella")), number="2026-009", date=days(-10))
        old = invoice(session, contract(session, client(session, "Acme"), title="Old"), number="2025-100", paid=True)
        r = rule(session, created=made(0), title="Thank {client} for paying invoice {invoice}", event="invoice=paid")
        inv.paid = True
        session.add(inv)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["Thank Umbrella for paying invoice 2026-009"]
        assert old.id not in {t.subject_id for t in tasks_of(session, r)}

    def test_contract_completed(self, session):
        ct = contract(session, client(session), title="Retainer")
        r = rule(session, created=made(0), title="Wrap up {contract} with {client}", event="contract=Completed")
        ct.is_completed = True
        session.add(ct)
        session.commit()
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["Wrap up Retainer with Acme"]

    def test_a_scoped_status_rule_watches_only_its_client(self, session):
        acme, umbrella = client(session, "Acme"), client(session, "Umbrella")
        r = rule(session, created=made(0), title="{project}", event="project=Lead", client_id=umbrella.id)
        project(session, contract(session, acme, title="A"), title="Acme lead", stage="Lead")
        project(session, contract(session, umbrella, title="U"), title="Umbrella lead", stage="Lead")
        generate_tasks(session, TODAY)
        assert [t.title for t in tasks_of(session, r)] == ["Umbrella lead"]

    def test_preview_of_a_new_rule_on_an_open_status(self, session):
        project(session, contract(session, client(session)), title="Underfloor Heating", stage="Offer")
        draft = TaskRule(title="Follow up on {project}", kind="event", event="project=Offer", offset=7, created_at=made(0))
        ev = evaluate(draft, session, TODAY)
        assert (ev.next.title, ev.next.trigger) == ("Follow up on Underfloor Heating", days(7))

    def test_preview_of_a_new_rule_on_a_final_status_makes_nothing_yet(self, session):
        project(session, contract(session, client(session)), title="Old job", stage="Completed")
        draft = TaskRule(title="Feedback on {project}", kind="event", event="project=Completed", created_at=made(0))
        ev = evaluate(draft, session, TODAY)
        assert (ev.items, ev.next) == ([], None)
