"""Task rules: what each rule asks for on a given day.

A rule either falls on a date, once or repeating, or follows something that
happens to a contract, project, invoice or financial goal. ``evaluate`` reads
the records and says, for one day, which tasks the rule wants, which subjects'
tasks are settled, and when it next creates one. The generator applies that to
the task table; the rule composer shows it as a preview.

A date can be anticipated, so a task may come before it. A state change, such
as a project becoming an offer, has no date of its own: the rule notes the
day it first sees it (``TaskRuleNotice``), and only reacts to changes from the
day it was made.
"""

import calendar
import datetime
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from sqlmodel import Session, select

from ...model import (
    Contract,
    FinancialGoal,
    Invoice,
    Project,
    TaskRule,
    TaskRuleNotice,
)
from ...time import Cycle

# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def fmt_date(d: datetime.date) -> str:
    return f"{MONTHS[d.month - 1][:3]} {d.day}, {d.year}"


def add_months(d: datetime.date, n: int, day: Optional[int] = None) -> datetime.date:
    """``d`` moved by ``n`` months, on ``day`` (default: d's day), kept within the month."""
    m = d.month - 1 + n
    year, month = d.year + m // 12, m % 12 + 1
    return datetime.date(year, month, min(day or d.day, calendar.monthrange(year, month)[1]))


def shift(d: datetime.date, amount: int, unit: str) -> datetime.date:
    if unit == "day":
        return d + datetime.timedelta(days=amount)
    if unit == "week":
        return d + datetime.timedelta(weeks=amount)
    return add_months(d, amount)


# ---------------------------------------------------------------------------
# What a rule can follow
#
# Each kind of record declares its dates and the statuses Tuttle already shows
# for it (the project board's stage, a contract's or an invoice's status). The
# events a rule can follow are derived from that: "a contract ends", "a
# project becomes an offer".
# ---------------------------------------------------------------------------


def _client_name(client) -> str:
    return client.name if client else ""


@dataclass(frozen=True)
class DateField:
    """A date on a record that a task can come before, on or after."""

    label: str  # reads after the record: "a contract ends"
    titles: tuple[Optional[str], str]  # default task titles: before or on the day, and after
    get: Callable[[object, datetime.date], list]  # the date, or dates up to a horizon
    is_open: Callable[[object], bool] = lambda _: True  # whether a task about it is still worth doing
    known_ahead: bool = True  # False: Tuttle learns the date only once it has passed
    # Open invoices and goals: tasks catch up on ones open before the rule was
    # made, and close once paid or reached, however late the task.
    lasting: bool = False
    repeats: bool = False


@dataclass(frozen=True)
class State:
    """A status a record can enter. A rule reacts when it does."""

    label: str  # "becomes an offer"
    title: str  # default task title
    # A final status (paid, completed) is where records end up, so it holds for
    # every old one: a rule counts only records that reach it from the day it's
    # made. An open one (overdue, an offer) is something to act on, so records
    # already in it count too.
    final: bool = False


@dataclass(frozen=True)
class Record:
    model: type
    label: str
    placeholders: tuple[str, ...]
    values: Callable[[object], dict]
    client_id: Callable[[object], Optional[int]]
    status: Callable[[object], str]  # the status Tuttle shows for it
    dates: dict[str, DateField]
    states: dict[str, State]  # the statuses a rule can follow, by status


def _contract_open(c: Contract) -> bool:
    return not c.is_completed


def _project_open(p: Project) -> bool:
    return not p.is_completed and p.stage != "Completed"


def _invoice_unsent(i: Invoice) -> bool:
    return not i.sent and not i.cancelled


def _invoice_unpaid(i: Invoice) -> bool:
    """Sent and still waiting for payment. Once a reminder is made, the reminder is what's open."""
    return bool(i.sent) and not i.paid and not i.cancelled and not i.reminders


_CYCLE_MONTHS = {Cycle.monthly: 1, Cycle.quarterly: 3, Cycle.yearly: 12}


def _period_ends(c: Contract, until: datetime.date) -> list[datetime.date]:
    """The last days of the contract's billing periods, up to ``until`` and its end date.

    Hourly and daily cycles have no period worth a task.
    """
    if c.billing_cycle == Cycle.weekly:

        def period_start(k: int) -> datetime.date:
            return c.start_date + datetime.timedelta(weeks=k)

    elif c.billing_cycle in _CYCLE_MONTHS:
        months = _CYCLE_MONTHS[c.billing_cycle]

        def period_start(k: int) -> datetime.date:
            return add_months(c.start_date, k * months, c.start_date.day)

    else:
        return []
    ends = []
    k = 1
    while True:
        end = period_start(k) - datetime.timedelta(days=1)
        if c.end_date and end >= c.end_date:
            if c.end_date <= until:
                ends.append(c.end_date)
            return ends
        if end > until:
            return ends
        ends.append(end)
        k += 1


RECORDS: dict[str, Record] = {
    "contract": Record(
        model=Contract,
        label="a contract",
        placeholders=("contract", "client", "date"),
        values=lambda c: {"contract": c.title, "client": _client_name(c.client)},
        client_id=lambda c: c.client_id,
        status=lambda c: c.status,
        dates={
            "signed": DateField(
                "is signed",
                ("{contract} is to be signed on {date}", "{contract} was signed on {date}"),
                get=lambda c, _: [c.signature_date],
                is_open=_contract_open,
            ),
            "start": DateField(
                "starts",
                ("{contract} starts on {date}", "{contract} started on {date}"),
                get=lambda c, _: [c.start_date],
                is_open=_contract_open,
            ),
            "end": DateField(
                "ends",
                ("{contract} ends on {date}", "{contract} ended on {date}"),
                get=lambda c, _: [c.end_date],
                is_open=_contract_open,
            ),
            "period_end": DateField(
                "ends a billing period",
                ("Billing period of {contract} ends on {date}", "Invoice {contract} for the period ending {date}"),
                get=_period_ends,
                is_open=_contract_open,
                repeats=True,
            ),
        },
        states={
            "Upcoming": State("is agreed", "Prepare the start of {contract}"),
            "Completed": State("is completed", "Wrap up {contract} with {client}", final=True),
        },
    ),
    "project": Record(
        model=Project,
        label="a project",
        placeholders=("project", "contract", "client", "date"),
        values=lambda p: {
            "project": p.title,
            "contract": p.contract.title if p.contract else "",
            "client": _client_name(p.client),
        },
        client_id=lambda p: p.contract.client_id if p.contract else None,
        status=lambda p: p.board_stage(),
        dates={
            "start": DateField(
                "starts",
                ("Project {project} starts on {date}", "Project {project} started on {date}"),
                get=lambda p, _: [p.start_date],
                is_open=_project_open,
            ),
            "end": DateField(
                "ends",
                ("Project {project} ends on {date}", "Project {project} ended on {date}"),
                get=lambda p, _: [p.end_date],
                is_open=_project_open,
            ),
        },
        states={
            "Lead": State("becomes a lead", "Follow up on the lead {project}"),
            "Offer": State("becomes an offer", "Follow up on the offer for {project}"),
            "Upcoming": State("is agreed", "Plan the start of {project}"),
            "Completed": State("is completed", "Ask {client} for feedback on {project}", final=True),
        },
    ),
    "invoice": Record(
        model=Invoice,
        label="an invoice",
        placeholders=("invoice", "client", "contract", "project", "date"),
        values=lambda i: {
            "invoice": i.number or "",
            "client": _client_name(i.contract.client) if i.contract else "",
            "contract": i.contract.title if i.contract else "",
            "project": i.project.title if i.project else "",
        },
        client_id=lambda i: i.contract.client_id if i.contract else None,
        status=lambda i: i.status,
        dates={
            "created": DateField(
                "is created",
                (None, "Send invoice {invoice} to {client}"),
                get=lambda i, _: [i.date],
                is_open=_invoice_unsent,
                known_ahead=False,
                lasting=True,
            ),
            "sent": DateField(
                "is sent",
                (None, "Check that {client} received invoice {invoice}"),
                get=lambda i, _: [i.sent_date if i.sent else None],
                is_open=_invoice_unpaid,
                known_ahead=False,
                lasting=True,
            ),
            "due": DateField(
                "is due",
                ("Invoice {invoice} to {client} is due on {date}", "Invoice {invoice} is overdue — send a reminder"),
                get=lambda i, _: [i.effective_due_date],
                is_open=_invoice_unpaid,
                lasting=True,
            ),
        },
        states={
            "overdue": State("becomes overdue", "Invoice {invoice} is overdue — send a reminder"),
            "paid": State("is paid", "Thank {client} for paying invoice {invoice}", final=True),
            "cancelled": State("is cancelled", "Invoice {invoice} was cancelled — issue a new one", final=True),
        },
    ),
    "goal": Record(
        model=FinancialGoal,
        label="a financial goal",
        placeholders=("goal", "date"),
        values=lambda g: {"goal": g.title},
        client_id=lambda g: None,
        status=lambda g: "reached" if g.is_reached else "open",
        dates={
            "target": DateField(
                "reaches its target date",
                ("{goal} is due on {date}", "{goal} was due on {date}"),
                get=lambda g, _: [g.target_date],
                is_open=lambda g: not g.is_reached,
                lasting=True,
            ),
        },
        states={"reached": State("is reached", "{goal} is reached", final=True)},
    ),
}


@dataclass(frozen=True)
class Event:
    """Something a rule follows: a date on a record ("contract.end") or a status it enters ("project=Offer")."""

    key: str
    record: str
    label: str
    titles: tuple[Optional[str], str]
    date: Optional[DateField] = None
    state: Optional[str] = None

    @property
    def is_state(self) -> bool:
        return self.state is not None

    @property
    def after_only(self) -> bool:
        """Known only once it has happened, so a task can only come after it."""
        return self.is_state or not self.date.known_ahead

    @property
    def final(self) -> bool:
        """A status records end up in, which a rule counts only from the day it's made."""
        return self.is_state and RECORDS[self.record].states[self.state].final

    def holds(self, obj) -> bool:
        return RECORDS[self.record].status(obj) == self.state


def _derive_events() -> dict[str, Event]:
    events = {}
    for rk, record in RECORDS.items():
        for dk, f in record.dates.items():
            events[f"{rk}.{dk}"] = Event(f"{rk}.{dk}", rk, f.label, f.titles, date=f)
        for status, st in record.states.items():
            events[f"{rk}={status}"] = Event(f"{rk}={status}", rk, st.label, (None, st.title), state=status)
    return events


EVENTS = _derive_events()


def rule_options() -> dict:
    """What the rule composer offers: each kind of record and the events it has."""
    return {
        "records": [
            {
                "key": rk,
                "label": record.label,
                "placeholders": list(record.placeholders),
                "events": [
                    {
                        "key": e.key,
                        "label": e.label,
                        "state": e.is_state,
                        "final": e.final,
                        "after_only": e.after_only,
                        "title_before": e.titles[0],
                        "title_after": e.titles[1],
                    }
                    for e in EVENTS.values()
                    if e.record == rk
                ],
            }
            for rk, record in RECORDS.items()
        ]
    }


def validate_rule(rule: TaskRule) -> None:
    """``TaskRule.validate_rule``, plus what only the event catalog knows. Raises ``ValueError``."""
    rule.validate_rule()
    if rule.kind != "event":
        return
    event = EVENTS.get(rule.event or "")
    if event is None:
        raise ValueError("Choose what the task follows, such as a contract ending.")
    if rule.before and event.after_only:
        raise ValueError("Tuttle learns of this only once it has happened. Choose a time after it.")
    if event.record == "goal":
        rule.client_id = None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def render(template: Optional[str], values: dict) -> Optional[str]:
    """Fill ``{placeholders}``. Anything else, including unknown placeholders, stays as typed."""
    if not template:
        return template
    return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), template)


def period_before(occurrence: datetime.date, rule: TaskRule) -> str:
    """The period a scheduled task looks back on: the month before a monthly one, and so on."""
    if rule.unit == "week":
        monday = occurrence - datetime.timedelta(days=occurrence.weekday() + 7)
        return f"the week of {fmt_date(monday)}"
    if rule.unit == "month" and rule.every == 12:
        return str(occurrence.year - 1)
    if rule.unit == "month" and rule.every == 6:
        p = add_months(occurrence, -6, 1)
        return f"H{1 if p.month <= 6 else 2} {p.year}"
    if rule.unit == "month" and rule.every == 3:
        p = add_months(occurrence, -3, 1)
        return f"Q{(p.month - 1) // 3 + 1} {p.year}"
    p = add_months(occurrence, -1, 1)
    return f"{MONTHS[p.month - 1]} {p.year}"


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


@dataclass
class Item:
    """A task a rule wants, or knows it will want."""

    key: str
    title: str
    note: Optional[str]
    due_date: datetime.date  # what the task is about: the event's date, or the scheduled day
    trigger: datetime.date  # the day the task appears
    subject_type: Optional[str] = None
    subject_id: Optional[int] = None
    # False for a date the rule leaves alone: an existing task keeps its title, but none appears.
    wanted: bool = True

    def is_due(self, today: datetime.date) -> bool:
        return self.wanted and self.trigger <= today

    def is_upcoming(self, today: datetime.date) -> bool:
        return self.wanted and self.trigger > today


@dataclass
class Evaluation:
    # Tasks that should exist today (trigger reached), and known ones still to come.
    items: list[Item] = field(default_factory=list)
    # Subjects whose pending tasks are no longer worth doing.
    settled: set[int] = field(default_factory=set)
    # Every subject the rule covers; None for a rule on a date.
    subjects: Optional[set[int]] = None
    # A state rule: subjects it noticed today.
    noticed: list[int] = field(default_factory=list)
    next: Optional[Item] = None


def created_on(rule: TaskRule, today: datetime.date) -> datetime.date:
    return rule.created_at.date() if rule.created_at else today


def occurrences(rule: TaskRule, until: datetime.date):
    """The days a rule on a date falls on, up to ``until``."""
    k = 0
    while True:
        if rule.unit == "week":
            d = rule.start_date + datetime.timedelta(weeks=k * rule.every)
        elif rule.unit == "month":
            d = add_months(rule.start_date, k * rule.every, rule.start_date.day)
        else:
            d = rule.start_date if k == 0 else None
        if d is None or d > until:
            return
        yield d
        k += 1


def _evaluate_date(rule: TaskRule, today: datetime.date) -> Evaluation:
    ev = Evaluation()
    start = created_on(rule, today)
    latest = None
    for d in occurrences(rule, add_months(today, 25)):
        if d < start:
            continue
        if d > today:
            ev.next = _scheduled_item(rule, d)
            break
        latest = d
    if latest:
        ev.items.append(_scheduled_item(rule, latest))
    return ev


def _scheduled_item(rule: TaskRule, d: datetime.date) -> Item:
    values = {"period": period_before(d, rule), "date": fmt_date(d)}
    return Item(
        key=f"rule:{rule.id}:{d.isoformat()}",
        title=render(rule.title, values),
        note=render(rule.note, values),
        due_date=d,
        trigger=d,
    )


def is_known(rule: TaskRule) -> bool:
    """Whether Tuttle can follow the rule: a date, or an event it knows (a newer version may know more)."""
    return rule.kind == "date" or rule.event in EVENTS


class Records:
    """Each kind of record, loaded once and shared by every rule that looks at it."""

    def __init__(self, session: Session):
        self.session = session
        self._loaded: dict[type, list] = {}

    def of(self, model: type) -> list:
        if model not in self._loaded:
            self._loaded[model] = self.session.exec(select(model)).all()
        return self._loaded[model]


def evaluate(
    rule: TaskRule,
    session: Session,
    today: datetime.date,
    notices: Optional[dict[int, TaskRuleNotice]] = None,
    records: Optional[Records] = None,
) -> Evaluation:
    """What ``rule`` asks for on ``today``.

    ``notices`` are a state rule's notes, by subject id. Without them the rule
    is taken as made today: a final status counts only from tomorrow's changes,
    and records in an open one count as noticed today.
    Pass ``records`` to share loaded records between rules.
    """
    if rule.kind == "date":
        return _evaluate_date(rule, today)
    if not is_known(rule):
        return Evaluation()
    event = EVENTS[rule.event]
    record = RECORDS[event.record]
    records = records or Records(session)
    objs = [o for o in records.of(record.model) if not rule.client_id or record.client_id(o) == rule.client_id]
    ev = Evaluation(subjects={o.id for o in objs})
    if event.is_state:
        _evaluate_state(rule, event, record, objs, today, notices, ev)
    else:
        _evaluate_dates(rule, event, record, objs, today, ev)
    upcoming = [i for i in ev.items if i.is_upcoming(today)]
    if upcoming:
        ev.next = min(upcoming, key=lambda i: i.trigger)
    return ev


def _item(rule, event, record, obj, d, trigger, key_suffix="", wanted=True) -> Item:
    values = {**record.values(obj), "date": fmt_date(d)}
    return Item(
        key=f"rule:{rule.id}:{event.record}:{obj.id}{key_suffix}",
        title=render(rule.title, values),
        note=render(rule.note, values),
        due_date=d,
        trigger=trigger,
        subject_type=event.record,
        subject_id=obj.id,
        wanted=wanted,
    )


def _evaluate_dates(rule, event, record, objs, today, ev: Evaluation) -> None:
    field_ = event.date
    start = created_on(rule, today)
    offset = -rule.offset if rule.before else rule.offset
    # A task after a contract or project date is a follow-up: it stays, however the
    # contract or project goes on. Before it, or on the day, it's a heads-up.
    guarded = field_.lasting or rule.before or rule.offset == 0
    horizon = shift(today + datetime.timedelta(days=400), rule.offset, rule.offset_unit)

    def creatable(d: datetime.date) -> bool:
        # Contract and project dates count from the day the rule was made;
        # a heads-up for a day that has passed is pointless.
        return (field_.lasting or d >= start) and not (rule.before and d < today)

    for obj in objs:
        if guarded and not field_.is_open(obj):
            ev.settled.add(obj.id)
            continue
        dates = [d for d in field_.get(obj, horizon) if d]
        if not field_.repeats:
            for d in dates:
                trigger = shift(d, offset, rule.offset_unit)
                ev.items.append(_item(rule, event, record, obj, d, trigger, wanted=creatable(d)))
            continue
        # A billing period recurs: the latest one due gets a task, older ones keep theirs.
        due, upcoming = None, None
        for d in dates:
            if not creatable(d):
                continue
            trigger = shift(d, offset, rule.offset_unit)
            if trigger <= today:
                due = (d, trigger)
            elif upcoming is None or trigger < upcoming[1]:
                upcoming = (d, trigger)
        for found in (due, upcoming):
            if found:
                ev.items.append(_item(rule, event, record, obj, *found, key_suffix=f":{found[0].isoformat()}"))


def _evaluate_state(rule, event, record, objs, today, notices, ev: Evaluation) -> None:
    for obj in objs:
        if not event.holds(obj):
            ev.settled.add(obj.id)
            continue
        if notices is None and event.final:
            continue
        notice = (notices or {}).get(obj.id)
        if notice is None:
            ev.noticed.append(obj.id)
            noticed_on = today
        elif notice.already:
            continue
        else:
            noticed_on = notice.noticed_on
        trigger = shift(noticed_on, rule.offset, rule.offset_unit)
        ev.items.append(_item(rule, event, record, obj, noticed_on, trigger, key_suffix=f":{noticed_on.isoformat()}"))


def start_watching(session: Session, rule: TaskRule, today: datetime.date) -> None:
    """Start a state rule afresh. For a final status, note every record already in it, so only later ones get a task."""
    for notice in session.exec(select(TaskRuleNotice).where(TaskRuleNotice.rule_id == rule.id)).all():
        session.delete(notice)
    session.flush()
    if not rule.follows_state or not is_known(rule) or not EVENTS[rule.event].final:
        return
    event = EVENTS[rule.event]
    record = RECORDS[event.record]
    for obj in session.exec(select(record.model)).all():
        if rule.client_id and record.client_id(obj) != rule.client_id:
            continue
        if event.holds(obj):
            session.add(TaskRuleNotice(rule_id=rule.id, subject_id=obj.id, noticed_on=today, already=True))
