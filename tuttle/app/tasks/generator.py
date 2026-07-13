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
        (
            "Contacts are the people you do business with — your clients' "
            "project leads, accountants, or anyone you need to address "
            "invoices to. Head over to Contacts in the sidebar and add "
            "someone you work with."
        ),
        Contact,
    ),
    (
        "tutorial:first_client",
        "Add your first client",
        (
            "A client is a company or person who pays you for your work. "
            "Each client can have multiple contacts and contracts. Go to "
            "Clients and create one — you can link a contact you already "
            "added as the invoicing recipient."
        ),
        Client,
    ),
    (
        "tutorial:first_contract",
        "Create your first contract",
        (
            "A contract captures the terms of your engagement: your hourly "
            "or daily rate, the billing cycle, currency, and payment terms. "
            "Open Contracts, pick the client, and fill in the details. This "
            "is what Tuttle uses to calculate invoices later."
        ),
        Contract,
    ),
    (
        "tutorial:first_project",
        "Set up your first project",
        (
            "Projects group your tracked time and invoices under a contract. "
            "Think of them as the actual work you deliver — e.g. 'Website "
            "Redesign Q3'. Create one under Projects and link it to your "
            "contract."
        ),
        Project,
    ),
    (
        "tutorial:first_invoice",
        "Create your first invoice",
        (
            "Once you have a project with tracked time (or a fixed-price "
            "contract), you can generate a professional invoice. Go to "
            "Invoicing, hit Create, pick a project and date range — Tuttle "
            "fills in the line items from your time records."
        ),
        Invoice,
    ),
]

# Tutorial tasks that don't auto-resolve (user must dismiss or complete them).
# (key, title, description)
TUTORIAL_MANUAL_RULES: list[tuple[str, str, str]] = [
    (
        "tutorial:configure_ai",
        "Configure AI assistant",
        (
            "Tuttle can use a large language model to read documents and "
            "extract data — like pulling contact info from a PDF or parsing "
            "an existing invoice. You can connect a local model (e.g. Ollama "
            "running on your machine) or a remote API (OpenAI, Anthropic, "
            "etc.). Head to Settings → AI / LLM to configure your endpoint."
        ),
    ),
    (
        "tutorial:import_document",
        "Import data from a document",
        (
            "Have an existing invoice, contract, or contact sheet as a PDF? "
            "Use the Import view to drag-and-drop it in. Tuttle's AI will "
            "read the document, extract the relevant data, and let you "
            "review before saving. This is the fastest way to get your "
            "existing business data into the app."
        ),
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


def _generate_tutorial_tasks(session: Session) -> None:
    """Auto-resolving tutorial tasks (condition-based)."""
    for key, title, description, model_cls in TUTORIAL_RULES:
        has_entity = session.exec(select(model_cls)).first() is not None
        existing = session.exec(select(Task).where(Task.key == key)).first()

        # Ensure task row exists
        if not existing:
            existing = Task(key=key, title=title, description=description)
            session.add(existing)
            session.flush()

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
        existing = session.exec(select(Task).where(Task.key == key)).first()
        if not existing:
            session.add(Task(key=key, title=title, description=description))


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
