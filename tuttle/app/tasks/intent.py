import datetime
from typing import Optional

from loguru import logger
from sqlmodel import Session, select

from ...model import Client, Task, TaskRule, TaskRuleNotice
from ..core.abstractions import Intent, SQLModelDataSourceMixin
from ..core.intent_result import IntentResult
from .generator import generate_tasks
from .rules import EVENTS, Records, evaluate, fmt_date, occurrences, rule_options, start_watching, validate_rule

# The fields that decide which tasks a rule makes. Changing one starts its pending tasks afresh.
_TRIGGER_FIELDS = ("kind", "start_date", "every", "unit", "event", "offset", "offset_unit", "before", "client_id")
# The fields that decide which records a status rule watches.
_WATCH_FIELDS = ("kind", "event", "client_id")


class TasksIntent(SQLModelDataSourceMixin, Intent):
    """Tasks CRUD with generator-driven refresh."""

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)

    def get_all(self) -> IntentResult:
        """Refresh tasks from business state, then return all non-dismissed."""
        try:
            with self.create_session() as session:
                generate_tasks(session)
            with self.create_session() as session:
                tasks = session.exec(
                    select(Task).where(Task.status.in_(["pending", "done"]))  # type: ignore[union-attr]
                ).all()
                return IntentResult(was_intent_successful=True, data=tasks)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to load tasks.",
                log_message=f"TasksIntent.get_all: {e}",
                exception=e,
            )

    def pending_count(self) -> int:
        """How many tasks are pending, after refreshing them from business state. For the sidebar."""
        try:
            with self.create_session() as session:
                generate_tasks(session)
                return len(session.exec(select(Task.id).where(Task.status == "pending")).all())
        except Exception:
            # The count is a convenience; the Tasks view reports a real failure.
            logger.exception("TasksIntent.pending_count failed")
            return 0

    def mark_done(self, id: int) -> IntentResult:
        """Mark a task as done."""
        try:
            with self.create_session() as session:
                task = session.get(Task, id)
                if not task:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg="Task not found.",
                    )
                task.status = "done"
                session.add(task)
                session.commit()
                return IntentResult(was_intent_successful=True, data=task)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to mark task done.",
                log_message=f"TasksIntent.mark_done({id}): {e}",
                exception=e,
            )

    def dismiss(self, id: int) -> IntentResult:
        """Dismiss a task (hide without completing)."""
        try:
            with self.create_session() as session:
                task = session.get(Task, id)
                if not task:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg="Task not found.",
                    )
                task.status = "dismissed"
                session.add(task)
                session.commit()
                return IntentResult(was_intent_successful=True, data=task)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to dismiss task.",
                log_message=f"TasksIntent.dismiss({id}): {e}",
                exception=e,
            )

    def reopen(self, id: int) -> IntentResult:
        """Reopen a completed or dismissed task."""
        try:
            with self.create_session() as session:
                task = session.get(Task, id)
                if not task:
                    return IntentResult(
                        was_intent_successful=False,
                        error_msg="Task not found.",
                    )
                task.status = "pending"
                session.add(task)
                session.commit()
                return IntentResult(was_intent_successful=True, data=task)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to reopen task.",
                log_message=f"TasksIntent.reopen({id}): {e}",
                exception=e,
            )

    # -- Rules -------------------------------------------------------------

    def rule_options(self) -> IntentResult:
        """What the rule composer offers: kinds of record, their events, and the clients to narrow to."""
        try:
            with self.create_session() as session:
                clients = session.exec(select(Client).order_by(Client.name)).all()
                options = rule_options()
                options["clients"] = [{"id": c.id, "name": c.name} for c in clients]
                return IntentResult(was_intent_successful=True, data=options)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to load the rule options.",
                log_message=f"TasksIntent.rule_options: {e}",
                exception=e,
            )

    def get_rules(self) -> IntentResult:
        """Every rule, each with the day it next creates a task."""
        try:
            today = datetime.date.today()
            with self.create_session() as session:
                rules = session.exec(select(TaskRule).order_by(TaskRule.id)).all()
                records = Records(session)
                data = []
                for rule in rules:
                    ev = evaluate(rule, session, today, self._notices(session, rule), records)
                    d = rule.to_rpc_dict()
                    d["next_date"] = ev.next.trigger.isoformat() if ev.next else None
                    data.append(d)
                return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to load the task rules.",
                log_message=f"TasksIntent.get_rules: {e}",
                exception=e,
            )

    def preview_rule(self, rule: dict) -> IntentResult:
        """What a rule being composed would do: the tasks it makes today, and the next one.

        A rule that can't be saved yet is not an error here: the preview says what's missing.
        """
        try:
            today = datetime.date.today()
            with self.create_session() as session:
                existing = session.get(TaskRule, rule.get("id")) if rule.get("id") else None
                draft = TaskRule(title="", created_at=existing.created_at if existing else datetime.datetime.now())
                try:
                    _fill(draft, rule)
                    validate_rule(draft)
                except ValueError as e:
                    return IntentResult(was_intent_successful=True, data={"error": str(e)})
                draft.id = existing.id if existing else None
                watched = existing is not None and _same(existing, draft, _WATCH_FIELDS)
                ev = evaluate(draft, session, today, self._notices(session, existing) if watched else None)
                data = {
                    "error": None,
                    "now": [{"title": i.title, "date": i.due_date.isoformat()} for i in ev.items if i.is_due(today)],
                    "next": {"title": ev.next.title, "date": ev.next.trigger.isoformat()} if ev.next else None,
                    "later": [],
                    # A new rule on a final status (paid, completed) counts only what reaches it from today.
                    "from_today": draft.follows_state and EVENTS[draft.event].final and not watched,
                }
                if draft.kind == "date" and ev.next:
                    after = [
                        d for d in occurrences(draft, ev.next.trigger + datetime.timedelta(days=400)) if d > ev.next.trigger
                    ]
                    data["later"] = [fmt_date(d) for d in after[:2]]
                return IntentResult(was_intent_successful=True, data=data)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Couldn't preview the rule. Details are in the application log.",
                log_message=f"TasksIntent.preview_rule: {e}",
                exception=e,
            )

    def save_rule(self, rule: dict) -> IntentResult:
        """Create or update a rule, and refresh the tasks it makes."""
        try:
            today = datetime.date.today()
            with self.create_session() as session:
                existing = session.get(TaskRule, rule.get("id")) if rule.get("id") else None
                old = TaskRule(**existing.model_dump()) if existing else None
                target = existing or TaskRule(title="")
                try:
                    _fill(target, rule)
                    validate_rule(target)
                except ValueError as e:
                    return IntentResult(was_intent_successful=False, error_msg=str(e))
                session.add(target)
                session.flush()
                if old is None or not _same(old, target, _WATCH_FIELDS):
                    start_watching(session, target, today)
                if old is not None and not _same(old, target, _TRIGGER_FIELDS):
                    for task in session.exec(select(Task).where(Task.rule_id == target.id, Task.status == "pending")).all():
                        session.delete(task)
                session.commit()
                session.refresh(target)
                return IntentResult(was_intent_successful=True, data=target.to_rpc_dict())
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Couldn't save the rule. Details are in the application log.",
                log_message=f"TasksIntent.save_rule: {e}",
                exception=e,
            )

    def set_rule_paused(self, id: int, paused: bool) -> IntentResult:
        """Pause or resume a rule."""
        try:
            with self.create_session() as session:
                rule = session.get(TaskRule, id)
                if not rule:
                    return IntentResult(was_intent_successful=False, error_msg="That rule no longer exists.")
                rule.paused = bool(paused)
                # Resumed, a rule on a final status ignores what reached it while paused.
                # One on an open status keeps its notes, so nothing it already followed up comes twice.
                if not rule.paused and rule.follows_state and EVENTS[rule.event].final:
                    start_watching(session, rule, datetime.date.today())
                session.add(rule)
                session.commit()
                session.refresh(rule)
                return IntentResult(was_intent_successful=True, data=rule.to_rpc_dict())
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Couldn't change the rule. Details are in the application log.",
                log_message=f"TasksIntent.set_rule_paused({id}): {e}",
                exception=e,
            )

    def delete_rule(self, id: int) -> IntentResult:
        """Delete a rule and the tasks it made."""
        try:
            with self.create_session() as session:
                rule = session.get(TaskRule, id)
                if not rule:
                    return IntentResult(was_intent_successful=True, data=None)
                for task in session.exec(select(Task).where(Task.rule_id == id)).all():
                    session.delete(task)
                for notice in session.exec(select(TaskRuleNotice).where(TaskRuleNotice.rule_id == id)).all():
                    session.delete(notice)
                session.delete(rule)
                session.commit()
                return IntentResult(was_intent_successful=True, data=None)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg="Couldn't delete the rule. Details are in the application log.",
                log_message=f"TasksIntent.delete_rule({id}): {e}",
                exception=e,
            )

    @staticmethod
    def _notices(session: Session, rule: Optional[TaskRule]) -> Optional[dict]:
        if rule is None or not rule.follows_state:
            return None
        return {n.subject_id: n for n in session.exec(select(TaskRuleNotice).where(TaskRuleNotice.rule_id == rule.id)).all()}


def _same(a: TaskRule, b: TaskRule, fields) -> bool:
    return all(getattr(a, f) == getattr(b, f) for f in fields)


def _int(value, message: str) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        raise ValueError(message) from None


def _fill(rule: TaskRule, data: dict) -> None:
    """Copy the composer's fields onto ``rule``. Raises ``ValueError`` with a message for the user."""
    rule.title = str(data.get("title") or "")
    rule.note = data.get("note") or None
    rule.kind = data.get("kind") or "date"
    start = data.get("start_date")
    try:
        rule.start_date = datetime.date.fromisoformat(start[:10]) if start else None
    except ValueError:
        raise ValueError("Enter the date as a calendar date.") from None
    rule.every = _int(data.get("every", 1), "Enter how often the task repeats as a whole number.")
    rule.unit = data.get("unit") or None
    rule.event = data.get("event") or None
    rule.offset = _int(data.get("offset", 0), "Enter how many days, weeks or months as a whole number.")
    rule.offset_unit = data.get("offset_unit") or "day"
    rule.before = bool(data.get("before"))
    client_id = data.get("client_id")
    rule.client_id = _int(client_id, "Choose a client from the list.") if client_id not in (None, "") else None
    if "paused" in data:
        rule.paused = bool(data["paused"])
