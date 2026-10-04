"""Task generator — inspects business state and upserts Task rows.

Called by TasksIntent.get_all() before returning results.  Each rule
produces a (key, title, description) tuple; the generator upserts by key
so duplicates are never created.

Tutorial tasks auto-resolve (mark done) when their condition no longer
holds.  Business tasks require explicit user action.
"""

from sqlmodel import Session, select

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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_tasks(session: Session) -> None:
    """Refresh task rows based on current business state."""
    _generate_tutorial_tasks(session)
    _generate_manual_tutorial_tasks(session)
    _generate_overdue_tasks(session)
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


def _generate_overdue_tasks(session: Session) -> None:
    invoices = session.exec(select(Invoice)).all()
    for inv in invoices:
        if inv.status != "overdue":
            continue
        # Skip if a reminder already exists for this invoice
        if inv.reminders:
            continue

        key = f"overdue:{inv.id}"
        existing = session.exec(select(Task).where(Task.key == key)).first()
        if not existing:
            session.add(
                Task(
                    key=key,
                    title=f"Invoice {inv.number} is overdue — send a reminder",
                    description=f"This invoice was due on {inv.effective_due_date}.",
                )
            )
