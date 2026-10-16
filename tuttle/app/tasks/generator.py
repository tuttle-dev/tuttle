"""Task generator — inspects business state and upserts Task rows.

Called by TasksIntent.get_all() before returning results. Tasks are keyed,
so the generator never creates one twice.

Tutorial tasks are built in and auto-resolve (mark done) when their condition
no longer holds. Every other task comes from a rule the user can edit (see
rules.py): it appears when the rule's day comes, and closes by itself when
it's no longer worth doing, such as a reminder for an invoice that got paid.
"""

import datetime
from typing import Optional

from sqlmodel import Session, select

from ...model import Client, Contact, Contract, Invoice, Project, Task, TaskRule, TaskRuleNotice
from .rules import Evaluation, Records, evaluate, is_known

# ---------------------------------------------------------------------------
# Tutorial rule definitions
# ---------------------------------------------------------------------------

TUTORIAL_RULES: list[tuple[str, str, str, type]] = [
    # (key, title, description, model_to_count)
    (
        "tutorial:first_contact",
        "Add your first contact",
        "Contacts are the people you send invoices to.",
        Contact,
    ),
    (
        "tutorial:first_client",
        "Add your first client",
        "A client is a company or person who pays you.",
        Client,
    ),
    (
        "tutorial:first_contract",
        "Create your first contract",
        "Set your rate, billing cycle and payment terms.",
        Contract,
    ),
    (
        "tutorial:first_project",
        "Set up your first project",
        "Projects group tracked time and invoices under a contract.",
        Project,
    ),
    (
        "tutorial:first_invoice",
        "Create your first invoice",
        "Turn tracked time into an invoice.",
        Invoice,
    ),
]

# Tutorial tasks that don't auto-resolve (user must dismiss or complete them).
# (key, title, description)
TUTORIAL_MANUAL_RULES: list[tuple[str, str, str]] = [
    (
        "tutorial:configure_ai",
        "Configure AI assistant",
        "Connect a language model to read documents for you.",
    ),
    (
        "tutorial:import_document",
        "Import data from a document",
        "Let AI pull contacts, contracts or invoices from a PDF.",
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_tasks(session: Session, today: Optional[datetime.date] = None) -> None:
    """Refresh task rows based on current business state."""
    today = today or datetime.date.today()
    _generate_tutorial_tasks(session)
    _generate_manual_tutorial_tasks(session)
    _generate_rule_tasks(session, today)
    session.commit()


# ---------------------------------------------------------------------------
# Tutorial tasks
# ---------------------------------------------------------------------------


def _upsert_tutorial_task(session: Session, key: str, title: str, description: str) -> Task:
    """Create the task row, or refresh its copy if the wording has changed."""
    existing = session.exec(select(Task).where(Task.key == key)).first()
    if not existing:
        existing = Task(key=key, title=title, description=description)
        session.add(existing)
        session.flush()
    elif existing.title != title or existing.description != description:
        existing.title = title
        existing.description = description
        session.add(existing)
    return existing


def _generate_tutorial_tasks(session: Session) -> None:
    """Auto-resolving tutorial tasks (condition-based)."""
    for key, title, description, model_cls in TUTORIAL_RULES:
        # Only the id: a whole record loads its relationships too, and this runs on every view change.
        has_entity = session.exec(select(model_cls.id).limit(1)).first() is not None
        existing = _upsert_tutorial_task(session, key, title, description)

        # Resolve or reopen based on current state
        if has_entity and existing.status == "pending":
            existing.status = "done"
            session.add(existing)
        elif not has_entity and existing.status == "done":
            existing.status = "pending"
            session.add(existing)


def _generate_manual_tutorial_tasks(session: Session) -> None:
    """Tutorial tasks that only disappear when the user dismisses them."""
    for key, title, description in TUTORIAL_MANUAL_RULES:
        _upsert_tutorial_task(session, key, title, description)


# ---------------------------------------------------------------------------
# Tasks from rules
# ---------------------------------------------------------------------------


def _generate_rule_tasks(session: Session, today: datetime.date) -> None:
    records = Records(session)
    for rule in session.exec(select(TaskRule).where(TaskRule.paused == False)).all():  # noqa: E712
        if not is_known(rule):
            # Its tasks are left as they are rather than taken for orphans.
            continue
        notices = None
        if rule.follows_state:
            notices = {
                n.subject_id: n for n in session.exec(select(TaskRuleNotice).where(TaskRuleNotice.rule_id == rule.id)).all()
            }
        ev = evaluate(rule, session, today, notices, records)
        _apply(session, rule, ev, today)
        if notices is not None:
            _note_changes(session, rule, ev, notices, today)


def _apply(session: Session, rule: TaskRule, ev: Evaluation, today: datetime.date) -> None:
    """Make the rule's tasks match what it asks for today."""
    tasks = session.exec(select(Task).where(Task.rule_id == rule.id)).all()
    by_key = {t.key: t for t in tasks}
    gone = set()
    for item in ev.items:
        task = by_key.get(item.key)
        if task is not None and task.due_date is not None and task.due_date != item.due_date:
            # The date moved, so the task was about another day.
            if not item.is_due(today):
                session.delete(task)
                gone.add(task.id)
                continue
            task.status = "pending"
            task.created_at = datetime.datetime.now()
        if task is None:
            if item.is_due(today):
                session.add(
                    Task(
                        key=item.key,
                        title=item.title,
                        description=item.note,
                        rule_id=rule.id,
                        due_date=item.due_date,
                        subject_type=item.subject_type,
                        subject_id=item.subject_id,
                    )
                )
            continue
        task.due_date = item.due_date
        if task.status == "pending":
            task.title, task.description = item.title, item.note
        session.add(task)
    for task in tasks:
        if task.id in gone or task.subject_id is None or task.status != "pending":
            continue
        if task.subject_id in ev.settled:
            task.status = "done"
            session.add(task)
        elif ev.subjects is not None and task.subject_id not in ev.subjects:
            # Its contract, project or invoice is gone, or no longer the rule's client's.
            session.delete(task)


def _note_changes(session: Session, rule: TaskRule, ev: Evaluation, notices: dict, today: datetime.date) -> None:
    """Remember the day a status change was first seen, and forget ones that were undone."""
    for subject_id in ev.noticed:
        session.add(TaskRuleNotice(rule_id=rule.id, subject_id=subject_id, noticed_on=today))
    for subject_id, notice in notices.items():
        if subject_id in ev.settled or (ev.subjects is not None and subject_id not in ev.subjects):
            session.delete(notice)
