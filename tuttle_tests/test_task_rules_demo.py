"""Task rules on Harry Tuttle's demo data, through the RPC calls the Tasks view makes.

The composer's payloads are sent exactly as the UI shapes them (see
ui/src/components/tasks/RuleComposer.tsx). test_task_rules_simulation.py runs
the rules over two years of days.
"""

import datetime
import json
from collections import Counter

import pytest
import sqlmodel
from sqlmodel import select

from tuttle.app.core.dispatch import dispatch
from tuttle.app.tasks.rules import EVENTS, RECORDS, add_months
from tuttle.model import Contract, FinancialGoal, Invoice, Project, TaskRule

TODAY = datetime.date.today()


@pytest.fixture
def db(harry_tuttle_db):
    """A session on the demo database. Rules a test adds are deleted afterwards, with their tasks."""
    engine = sqlmodel.create_engine(f"sqlite:///{harry_tuttle_db}")
    with sqlmodel.Session(engine) as session:
        before = {r.id for r in session.exec(select(TaskRule)).all()}
        yield session
    for rule_id in {r["id"] for r in ok(dispatch("tasks.get_rules", {}))} - before:
        ok(dispatch("tasks.delete_rule", {"id": rule_id}))
    engine.dispose()


def ok(result: dict):
    """The data of a successful RPC envelope, which must survive JSON like the real transport."""
    assert result["ok"] is True, result.get("error")
    json.dumps(result)
    return result["data"]


def ui_rule(**fields) -> dict:
    """A rule as the composer sends it: every field present, nulls included."""
    rule = {
        "title": "Task",
        "note": None,
        "kind": "event",
        "start_date": None,
        "every": 1,
        "unit": None,
        "event": "contract.end",
        "offset": 2,
        "offset_unit": "week",
        "before": True,
        "client_id": None,
        "paused": False,
    }
    rule.update(fields)
    return rule


def first_of_next_month() -> datetime.date:
    return add_months(TODAY.replace(day=1), 1)


# ---------------------------------------------------------------------------
# What the demo shows
# ---------------------------------------------------------------------------


class TestDemo:
    def test_built_in_rules_and_harrys_own(self, db):
        rules = ok(dispatch("tasks.get_rules", {}))
        signature = {(r["kind"], r["event"], r["offset"], r["before"], r["paused"]) for r in rules}
        # Every user starts with these two.
        assert ("event", "invoice.due", 1, False, False) in signature
        assert ("event", "contract.end", 30, True, False) in signature
        # Harry's own: dates once and repeating, status changes, a scoped one and a paused one.
        kinds = Counter(r["kind"] for r in rules)
        assert kinds["date"] == 3 and kinds["event"] == 5
        assert any(r["paused"] for r in rules)
        assert any(r["client_id"] for r in rules)
        dated = {r["title"]: r["next_date"] for r in rules if r["kind"] == "date"}
        assert dated["Send invoices for {period}"] == first_of_next_month().isoformat()

    def test_tasks_from_harrys_rules(self, db):
        tasks = ok(dispatch("tasks.get_all", {}))
        titles = {t["title"] for t in tasks if t["status"] == "pending"}
        last_month = add_months(TODAY.replace(day=1), -1)
        assert f"Send invoices for {last_month:%B %Y}" in titles
        assert any(t.startswith("File the VAT return for Q") for t in titles)
        assert "Follow up on the offer for Underfloor Heating" in titles

    def test_every_open_overdue_invoice_has_a_reminder_task(self, db):
        overdue_rule = next(r for r in ok(dispatch("tasks.get_rules", {})) if r["event"] == "invoice.due")
        tasks = [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == overdue_rule["id"]]
        expected = {
            i.id
            for i in db.exec(select(Invoice)).all()
            if i.sent
            and not i.paid
            and not i.cancelled
            and not i.reminders
            and i.effective_due_date
            and i.effective_due_date < TODAY
        }
        assert expected, "the demo should show an overdue invoice"
        assert {t["subject_id"] for t in tasks if t["status"] == "pending"} == expected
        for t in tasks:
            assert "{" not in t["title"] and t["title"].endswith("is overdue — send a reminder")

    def test_every_task_from_a_rule_points_at_a_record_that_exists(self, db):
        models = {"contract": Contract, "project": Project, "invoice": Invoice, "goal": FinancialGoal}
        for t in ok(dispatch("tasks.get_all", {})):
            if t["subject_type"]:
                assert db.get(models[t["subject_type"]], t["subject_id"]) is not None, t
            if t["rule_id"]:
                assert t["due_date"], t

    def test_pending_count_is_what_the_tasks_view_shows(self, db):
        pending = [t for t in ok(dispatch("tasks.get_all", {})) if t["status"] == "pending"]
        assert ok(dispatch("tasks.pending_count", {})) == len(pending)

    def test_options_name_harrys_clients(self, db):
        options = ok(dispatch("tasks.rule_options", {}))
        assert {"Central Services", "Ductwork Security Inc."} <= {c["name"] for c in options["clients"]}
        assert sum(len(r["events"]) for r in options["records"]) == len(EVENTS)


# ---------------------------------------------------------------------------
# The composer's calls
# ---------------------------------------------------------------------------


def _timings(event):
    yield "on", 0, False
    if not event.after_only:
        yield "before", 2, True
    yield "after", 2, False


CATALOG = [(key, timing, offset, before) for key, e in EVENTS.items() for timing, offset, before in _timings(e)]
# On the day needs no unit; before and after are tried in days and in months (which keep within month ends).
PREVIEWS = [(k, t, o, b, u) for k, t, o, b in CATALOG for u in (["day"] if t == "on" else ["day", "month"])]


class TestComposer:
    @pytest.mark.parametrize("key, timing, offset, before, unit", PREVIEWS, ids=[f"{k}-{t}-{u}" for k, t, _, _, u in PREVIEWS])
    def test_every_event_previews(self, db, key, timing, offset, before, unit):
        event = EVENTS[key]
        # As the composer suggests it: the heads-up title before or on the day, where there is one.
        heads_up = before or (timing == "on" and not event.is_state)
        title = (event.titles[0] or event.titles[1]) if heads_up else event.titles[1]
        preview = ok(
            dispatch(
                "tasks.preview_rule",
                {
                    "rule": ui_rule(title=title, event=key, offset=offset, offset_unit=unit, before=before),
                },
            )
        )
        assert preview["error"] is None
        placeholders = {f"{{{p}}}" for p in RECORDS[event.record].placeholders}
        for task in preview["now"] + ([preview["next"]] if preview["next"] else []):
            assert not any(p in task["title"] for p in placeholders), task
        # A new rule on a final status (paid, completed) counts only what reaches it from today.
        assert preview["from_today"] == event.final

    def test_monthly_preview(self, db):
        preview = ok(
            dispatch(
                "tasks.preview_rule",
                {
                    "rule": ui_rule(
                        kind="date",
                        title="Send invoices for {period}",
                        start_date=first_of_next_month().isoformat(),
                        unit="month",
                    )
                },
            )
        )
        first = first_of_next_month()
        assert preview["next"] == {"title": f"Send invoices for {TODAY:%B %Y}", "date": first.isoformat()}
        assert preview["later"] == [f"{d:%b} {d.day}, {d.year}" for d in (add_months(first, 1), add_months(first, 2))]

    def test_preview_of_a_day_that_has_passed(self, db):
        preview = ok(
            dispatch(
                "tasks.preview_rule",
                {
                    "rule": ui_rule(
                        kind="date",
                        title="Too late",
                        start_date=(TODAY - datetime.timedelta(days=3)).isoformat(),
                    )
                },
            )
        )
        assert (preview["error"], preview["now"], preview["next"]) == (None, [], None)

    def test_a_new_offer_rule_covers_the_offer_already_out(self, db):
        preview = ok(
            dispatch(
                "tasks.preview_rule",
                {"rule": ui_rule(title="Follow up on the offer for {project}", event="project=Offer", offset=1, before=False)},
            )
        )
        assert preview["from_today"] is False
        assert preview["next"]["title"] == "Follow up on the offer for Underfloor Heating"

    def test_editing_a_status_rule_previews_its_own_tasks(self, db):
        offer_rule = next(r for r in ok(dispatch("tasks.get_rules", {})) if r["event"] == "project=Offer")
        preview = ok(dispatch("tasks.preview_rule", {"rule": offer_rule}))
        assert preview["from_today"] is False
        assert [t["title"] for t in preview["now"]] == ["Follow up on the offer for Underfloor Heating"]

    @pytest.mark.parametrize(
        "fields, message",
        [
            ({"title": ""}, "Give the task a title."),
            ({"kind": "date", "start_date": None}, "Choose the date of the task."),
            ({"kind": "date", "start_date": "15.10.2026"}, "Enter the date as a calendar date."),
            ({"offset": "two"}, "Enter how many days, weeks or months as a whole number."),
            ({"every": "often", "kind": "date", "start_date": "2026-12-01"}, "whole number"),
            ({"client_id": "Acme"}, "Choose a client from the list."),
            ({"event": None}, "Choose what the task follows"),
            ({"event": "contract.explodes"}, "Choose what the task follows"),
            ({"event": "invoice.sent", "before": True}, "only once it has happened"),
            ({"event": "project=Offer", "before": True}, "only once it has happened"),
        ],
    )
    def test_preview_says_what_is_missing_and_save_refuses(self, db, fields, message):
        preview = ok(dispatch("tasks.preview_rule", {"rule": ui_rule(**fields)}))
        assert message in preview["error"]
        saved = dispatch("tasks.save_rule", {"rule": ui_rule(**fields)})
        assert saved["ok"] is False
        assert message in saved["error"]
        assert "Traceback" not in saved["error"] and "NoneType" not in saved["error"]

    def test_create_edit_pause_resume_delete(self, db):
        created = ok(
            dispatch(
                "tasks.save_rule",
                {
                    "rule": ui_rule(
                        kind="date",
                        title="Water the plants",
                        note="Every {period}",
                        start_date=TODAY.isoformat(),
                        unit="week",
                    )
                },
            )
        )
        rule_id = created["id"]
        tasks = [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == rule_id]
        assert [(t["title"], t["due_date"]) for t in tasks] == [("Water the plants", TODAY.isoformat())]

        edited = ok(dispatch("tasks.save_rule", {"rule": {**created, "title": "Water the ficus"}}))
        assert edited["id"] == rule_id
        tasks = [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == rule_id]
        assert [t["title"] for t in tasks] == ["Water the ficus"]

        assert ok(dispatch("tasks.set_rule_paused", {"id": rule_id, "paused": True}))["paused"] is True
        assert ok(dispatch("tasks.set_rule_paused", {"id": rule_id, "paused": False}))["paused"] is False

        ok(dispatch("tasks.delete_rule", {"id": rule_id}))
        assert rule_id not in {r["id"] for r in ok(dispatch("tasks.get_rules", {}))}
        assert not [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == rule_id]

    def test_changing_the_trigger_starts_pending_tasks_afresh(self, db):
        created = ok(
            dispatch(
                "tasks.save_rule",
                {"rule": ui_rule(title="{invoice} overdue", event="invoice.due", offset=1, offset_unit="day", before=False)},
            )
        )
        assert [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == created["id"]]
        # Ten years after it's due: no invoice of Harry's is that late.
        ok(dispatch("tasks.save_rule", {"rule": {**created, "offset": 120, "offset_unit": "month"}}))
        assert not [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == created["id"]]

    def test_a_final_status_rule_counts_from_the_day_it_is_made(self, db):
        created = ok(
            dispatch(
                "tasks.save_rule",
                {"rule": ui_rule(title="Thank {client}", event="invoice=paid", offset=0, before=False)},
            )
        )
        assert not [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == created["id"]]
        ok(dispatch("tasks.set_rule_paused", {"id": created["id"], "paused": True}))
        ok(dispatch("tasks.set_rule_paused", {"id": created["id"], "paused": False}))
        assert not [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == created["id"]]

    def test_an_open_status_rule_resumed_does_not_follow_up_twice(self, db):
        created = ok(
            dispatch(
                "tasks.save_rule",
                {"rule": ui_rule(title="Chase {project}", event="project=Offer", offset=0, before=False)},
            )
        )
        tasks = [t for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == created["id"]]
        assert [t["title"] for t in tasks] == ["Chase Underfloor Heating"]
        ok(dispatch("tasks.set_rule_paused", {"id": created["id"], "paused": True}))
        ok(dispatch("tasks.set_rule_paused", {"id": created["id"], "paused": False}))
        assert [t["id"] for t in ok(dispatch("tasks.get_all", {})) if t["rule_id"] == created["id"]] == [tasks[0]["id"]]

    def test_a_rule_for_every_event_keeps_the_tasks_view_loading(self, db):
        for key, timing, offset, before in CATALOG:
            event = EVENTS[key]
            ok(
                dispatch(
                    "tasks.save_rule",
                    {
                        "rule": ui_rule(
                            title=event.titles[1],
                            event=key,
                            offset=offset,
                            offset_unit="week",
                            before=before,
                        )
                    },
                )
            )
        tasks = ok(dispatch("tasks.get_all", {}))
        assert len({t["key"] for t in tasks}) == len(tasks)
        assert ok(dispatch("tasks.pending_count", {})) == sum(t["status"] == "pending" for t in tasks)
        rules = ok(dispatch("tasks.get_rules", {}))
        assert len(rules) >= len(CATALOG)

    def test_deleting_a_missing_rule_is_harmless(self, db):
        ok(dispatch("tasks.delete_rule", {"id": 999999}))
        assert dispatch("tasks.set_rule_paused", {"id": 999999, "paused": True})["error"] == "That rule no longer exists."
