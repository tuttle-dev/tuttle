"""Two years of days on Harry Tuttle's demo data, with a rule for every event in the catalog.

Every few days the generator runs twice. Tasks must come neither early nor
twice about the same record, stay done once ticked off, and a second pass on
the same day must change nothing.
"""

import datetime
import shutil
from collections import Counter

import sqlmodel
from sqlmodel import select

from tuttle.app.tasks.generator import generate_tasks
from tuttle.app.tasks.rules import EVENTS, shift, start_watching, validate_rule
from tuttle.model import Task, TaskRule

TODAY = datetime.date.today()

# Every event at every timing it allows: on the day (or as soon as), before, after.
CATALOG = [
    (key, timing, offset, before)
    for key, e in EVENTS.items()
    for timing, offset, before in [("on", 0, False), ("before", 2, True), ("after", 2, False)]
    if not (before and e.after_only)
]


def _trigger(rule: TaskRule, task: Task) -> datetime.date:
    """The day a task may first appear."""
    if rule.kind == "date":
        return task.due_date
    return shift(task.due_date, -rule.offset if rule.before else rule.offset, rule.offset_unit)


def test_two_years_of_days(harry_tuttle_db, tmp_path):
    copy = tmp_path / "harry.db"
    shutil.copy(harry_tuttle_db, copy)
    engine = sqlmodel.create_engine(f"sqlite:///{copy}")
    start = TODAY - datetime.timedelta(days=30)
    made = datetime.datetime.combine(start - datetime.timedelta(days=30), datetime.time(9))
    with sqlmodel.Session(engine) as session:
        # Every event at every timing (the units take turns), plus every repeat of a date rule.
        for i, (key, timing, offset, before) in enumerate(CATALOG):
            for unit in [("day", "week", "month")[i % 3]]:
                rule = TaskRule(
                    title=f"{key} {timing} {unit} {{date}}",
                    kind="event",
                    event=key,
                    offset=offset,
                    offset_unit=unit,
                    before=before,
                    created_at=made,
                )
                validate_rule(rule)
                session.add(rule)
                session.flush()
                start_watching(session, rule, made.date())
        for unit, every in ((None, 1), ("week", 1), ("week", 2), ("month", 1), ("month", 3), ("month", 6), ("month", 12)):
            for start_date in (start, datetime.date(start.year, 1, 31)):
                session.add(
                    TaskRule(
                        title=f"every {every} {unit} {{period}}",
                        kind="date",
                        start_date=start_date,
                        unit=unit,
                        every=every,
                        created_at=made,
                    )
                )
        session.commit()
        rules = {r.id: r for r in session.exec(select(TaskRule)).all()}

        def snapshot():
            return {t.key: (t.status, t.title, t.due_date) for t in session.exec(select(Task)).all()}

        done_keys: set[str] = set()
        for step in range(0, 730, 10):
            day = start + datetime.timedelta(days=step)
            before = snapshot()
            generate_tasks(session, day)
            after = snapshot()

            generate_tasks(session, day)
            assert snapshot() == after, f"a second pass on {day} changed tasks"

            new_tasks = [t for t in session.exec(select(Task).where(Task.rule_id.is_not(None))).all() if t.key not in before]
            per_subject = Counter((t.rule_id, t.subject_id) for t in new_tasks)
            assert max(per_subject.values(), default=0) <= 1, f"{day}: one rule made several tasks about one record"
            for t in new_tasks:
                rule = rules[t.rule_id]
                assert _trigger(rule, t) <= day, f"{day}: '{t.title}' came early (due {t.due_date})"
                assert "{" not in t.title, t.title

            for key in done_keys:
                assert after[key][0] == "done", f"{day}: done task {key} came back"

            if step == 300:
                # Harry ticks off everything; nothing ticked off may come back.
                for t in session.exec(select(Task).where(Task.status == "pending")).all():
                    t.status = "done"
                    session.add(t)
                session.commit()
                done_keys = {k for k, v in snapshot().items() if v[0] == "done"}

        # One task per record for a date that happens once.
        once = Counter(
            (t.rule_id, t.subject_id)
            for t in session.exec(select(Task).where(Task.subject_id.is_not(None))).all()
            if not EVENTS[rules[t.rule_id].event].is_state and not EVENTS[rules[t.rule_id].event].date.repeats
        )
        assert max(once.values()) == 1
        made_any = Counter(
            rules[t.rule_id].event or rules[t.rule_id].unit for t in session.exec(select(Task)).all() if t.rule_id
        )
        assert made_any["invoice.due"] and made_any["contract.period_end"] and made_any["month"]
    engine.dispose()
