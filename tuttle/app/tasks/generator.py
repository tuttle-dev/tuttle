"""Task generator — inspects business state and upserts Task rows.

Called by TasksIntent.get_all() before returning results.  Each rule
produces a (key, title, description) tuple; the generator upserts by key
so duplicates are never created.

Tutorial tasks auto-resolve (mark done) when their condition no longer
holds.  Business tasks require explicit user action.
"""

import datetime

from sqlmodel import Session, select

from ...app_db import AppDatabase
from ...model import Client, Contact, Contract, Invoice, Project, Task

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


def _parse_lead_days(raw: str) -> list[int]:
    """Parse a comma-separated string of non-negative integers."""
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return sorted(set(result), reverse=True)


def _load_lead_days() -> tuple[list[int], list[int]]:
    """Read task reminder lead-day settings from the app database."""
    app_db = AppDatabase()
    contract_raw = app_db.get_setting("tasks.contract_end_lead_days") or "30, 0"
    overdue_raw = app_db.get_setting("tasks.invoice_overdue_lead_days") or "0"
    return _parse_lead_days(contract_raw), _parse_lead_days(overdue_raw)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_tasks(session: Session) -> None:
    """Refresh task rows based on current business state."""
    _generate_tutorial_tasks(session)
    _generate_manual_tutorial_tasks(session)
    contract_leads, overdue_leads = _load_lead_days()
    _generate_overdue_tasks(session, overdue_leads)
    _generate_contract_end_tasks(session, contract_leads)
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
        has_entity = session.exec(select(model_cls)).first() is not None
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
# Overdue invoice tasks
# ---------------------------------------------------------------------------


def _generate_overdue_tasks(session: Session, lead_days: list[int]) -> None:
    if not lead_days:
        return
    invoices = session.exec(select(Invoice)).all()
    today = datetime.date.today()
    for inv in invoices:
        if inv.status != "overdue":
            continue
        if inv.reminders:
            continue
        due = inv.effective_due_date
        if not due:
            continue
        days_overdue = (today - due).days
        for d in lead_days:
            if days_overdue < d:
                continue
            key = f"overdue:{inv.id}" if d == 0 else f"overdue:{inv.id}:{d}"
            existing = session.exec(select(Task).where(Task.key == key)).first()
            if not existing:
                suffix = f" — {d} days overdue" if d > 0 else ""
                session.add(
                    Task(
                        key=key,
                        title=f"Invoice {inv.number} is overdue{suffix} — send a reminder",
                        description=f"This invoice was due on {due}.",
                    )
                )


# ---------------------------------------------------------------------------
# Contract-end tasks
# ---------------------------------------------------------------------------


def _generate_contract_end_tasks(session: Session, lead_days: list[int]) -> None:
    if not lead_days:
        return
    contracts = session.exec(select(Contract)).all()
    today = datetime.date.today()
    for c in contracts:
        if not c.end_date or c.is_completed:
            continue
        days_until_end = (c.end_date - today).days
        for d in lead_days:
            if days_until_end > d:
                continue
            key = f"contract_ending:{c.id}:{d}"
            existing = session.exec(select(Task).where(Task.key == key)).first()
            if not existing:
                if d == 0:
                    title = f"Contract \"{c.title}\" ends today"
                else:
                    title = f"Contract \"{c.title}\" ends in {d} days"
                session.add(
                    Task(
                        key=key,
                        title=title,
                        description=f"End date: {c.end_date}.",
                    )
                )
            elif existing.status == "pending" and c.is_completed:
                existing.status = "done"
                session.add(existing)
