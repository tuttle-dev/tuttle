"""Business logic for the timeline view.

Aggregates date-stamped events from invoices, contracts, projects and
financial goals into a single chronological feed.

Each entity produces at most one or two high-signal events to keep the
timeline scannable.
"""

import datetime
from dataclasses import dataclass
from typing import List, Optional

from ..core.abstractions import SQLModelDataSourceMixin, Intent
from ..core.intent_result import IntentResult
from ..core.formatting import fmt_currency
from ..res import colors

from ...model import Contract, Invoice, Project, FinancialGoal


# ── Category constants ────────────────────────────────────────

CATEGORY_INVOICE = "invoice"
CATEGORY_CONTRACT = "contract"
CATEGORY_PROJECT = "project"
CATEGORY_GOAL = "goal"

CATEGORY_COLORS = {
    CATEGORY_INVOICE: colors.accent,
    CATEGORY_CONTRACT: colors.success,
    CATEGORY_PROJECT: colors.warning,
    CATEGORY_GOAL: colors.goal_purple,
}

# Icon codepoints (Material Symbols).
ICON_RECEIPT_OUTLINED = 71694
ICON_HANDSHAKE_OUTLINED = 69034
ICON_WORK_OUTLINE = 74308
ICON_FLAG_OUTLINED = 68514
ICON_CANCEL_OUTLINED = 66730
ICON_CHECK_CIRCLE_OUTLINE = 66871
ICON_WARNING_AMBER_ROUNDED = 74074
ICON_SCHEDULE = 72057
ICON_EMOJI_EVENTS_OUTLINED = 68020

CATEGORY_ICONS = {
    CATEGORY_INVOICE: ICON_RECEIPT_OUTLINED,
    CATEGORY_CONTRACT: ICON_HANDSHAKE_OUTLINED,
    CATEGORY_PROJECT: ICON_WORK_OUTLINE,
    CATEGORY_GOAL: ICON_FLAG_OUTLINED,
}


@dataclass
class TimelineEvent:
    """A single event to render on the timeline.

    These are *derived* at display time — nothing is persisted.
    """

    date: datetime.date
    title: str
    description: str
    category: str
    icon: int
    color: str
    is_future: bool
    entity_id: Optional[int] = None


class TimelineIntent(SQLModelDataSourceMixin, Intent):
    """Gathers timeline events from all business entities."""

    def __init__(self):
        SQLModelDataSourceMixin.__init__(self)

    # ── Public API ────────────────────────────────────────────

    def get_events(
        self,
        category_filter: Optional[str] = None,
    ) -> IntentResult:
        """Return a date-descending list of `TimelineEvent` instances.

        If *category_filter* is set, only events of that category are
        included.
        """
        try:
            events: List[TimelineEvent] = []
            today = datetime.date.today()

            events.extend(self._events_from_invoices(today))
            events.extend(self._events_from_contracts(today))
            events.extend(self._events_from_projects(today))
            events.extend(self._events_from_goals(today))

            if category_filter:
                events = [e for e in events if e.category == category_filter]

            events.sort(key=lambda e: e.date, reverse=True)
            return IntentResult(was_intent_successful=True, data=events)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                error_msg=f"Failed to load timeline events: {e}",
                log_message=f"TimelineIntent.get_events: {e}",
                exception=e,
            )

    # ── Invoice events ────────────────────────────────────────
    # One event per invoice showing the most significant state,
    # plus a separate "due/overdue" marker for unpaid invoices.

    def _events_from_invoices(self, today: datetime.date) -> List[TimelineEvent]:
        invoices = self.query(Invoice)
        events: List[TimelineEvent] = []
        cat = CATEGORY_INVOICE
        color = CATEGORY_COLORS[cat]

        for inv in invoices:
            client_name = inv.client.name if inv.client else "—"
            try:
                currency = inv.contract.currency if inv.contract else "EUR"
                amount_str = fmt_currency(inv.total, currency)
            except Exception:
                amount_str = ""

            if inv.is_reminder:
                label = f"Reminder {inv.reminder_level} for {inv.number or ''}"
            else:
                label = f"Invoice {inv.number or ''}"
            desc = f"{client_name} · {amount_str}" if amount_str else client_name

            # Reminders always get a "sent" event on their date
            if inv.is_reminder:
                events.append(
                    TimelineEvent(
                        date=inv.date,
                        title=f"{label} sent",
                        description=desc,
                        category=cat,
                        icon=ICON_WARNING_AMBER_ROUNDED,
                        color=colors.warning,
                        is_future=inv.date > today,
                        entity_id=inv.id,
                    )
                )

            if inv.cancelled:
                events.append(
                    TimelineEvent(
                        date=inv.date,
                        title=f"{label} cancelled",
                        description=client_name,
                        category=cat,
                        icon=ICON_CANCEL_OUTLINED,
                        color=colors.danger,
                        is_future=False,
                        entity_id=inv.id,
                    )
                )
                continue

            if inv.paid:
                events.append(
                    TimelineEvent(
                        date=inv.date,
                        title=f"{label} paid",
                        description=desc,
                        category=cat,
                        icon=ICON_CHECK_CIRCLE_OUTLINE,
                        color=colors.success,
                        is_future=False,
                        entity_id=inv.id,
                    )
                )
                continue

            if not inv.is_reminder:
                events.append(
                    TimelineEvent(
                        date=inv.date,
                        title=label,
                        description=desc,
                        category=cat,
                        icon=CATEGORY_ICONS[cat],
                        color=color,
                        is_future=inv.date > today,
                        entity_id=inv.id,
                    )
                )

            due = inv.effective_due_date
            if due:
                is_overdue = due < today
                events.append(
                    TimelineEvent(
                        date=due,
                        title=f"{label} {'overdue' if is_overdue else 'due'}",
                        description=desc,
                        category=cat,
                        icon=ICON_WARNING_AMBER_ROUNDED
                        if is_overdue
                        else ICON_SCHEDULE,
                        color=colors.danger if is_overdue else color,
                        is_future=due > today,
                        entity_id=inv.id,
                    )
                )

        return events

    # ── Contract events ───────────────────────────────────────
    # "started" and optionally "ended/ending".

    def _events_from_contracts(self, today: datetime.date) -> List[TimelineEvent]:
        contracts = self.query(Contract)
        events: List[TimelineEvent] = []
        cat = CATEGORY_CONTRACT
        icon = CATEGORY_ICONS[cat]
        color = CATEGORY_COLORS[cat]

        for c in contracts:
            client_name = c.client.name if c.client else "—"
            label = c.title or "Contract"

            events.append(
                TimelineEvent(
                    date=c.start_date,
                    title=f"{label} started",
                    description=client_name,
                    category=cat,
                    icon=icon,
                    color=color,
                    is_future=c.start_date > today,
                    entity_id=c.id,
                )
            )

            if c.end_date:
                ended = c.end_date <= today
                events.append(
                    TimelineEvent(
                        date=c.end_date,
                        title=f"{label} {'ended' if ended else 'ending'}",
                        description=client_name,
                        category=cat,
                        icon=icon,
                        color=colors.status_completed if ended else color,
                        is_future=not ended,
                        entity_id=c.id,
                    )
                )

        return events

    # ── Project events ────────────────────────────────────────
    # "started" and optionally "completed/ending".

    def _events_from_projects(self, today: datetime.date) -> List[TimelineEvent]:
        projects = self.query(Project)
        events: List[TimelineEvent] = []
        cat = CATEGORY_PROJECT
        icon = CATEGORY_ICONS[cat]
        color = CATEGORY_COLORS[cat]

        for p in projects:
            client_name = p.client.name if p.client else ""
            label = p.title or "Project"

            events.append(
                TimelineEvent(
                    date=p.start_date,
                    title=f"{label} started",
                    description=client_name,
                    category=cat,
                    icon=icon,
                    color=color,
                    is_future=p.start_date > today,
                    entity_id=p.id,
                )
            )

            if p.is_completed:
                events.append(
                    TimelineEvent(
                        date=p.end_date,
                        title=f"{label} completed",
                        description=client_name,
                        category=cat,
                        icon=ICON_CHECK_CIRCLE_OUTLINE,
                        color=colors.success,
                        is_future=False,
                        entity_id=p.id,
                    )
                )
            elif p.end_date:
                ended = p.end_date <= today
                events.append(
                    TimelineEvent(
                        date=p.end_date,
                        title=f"{label} {'ended' if ended else 'ending'}",
                        description=client_name,
                        category=cat,
                        icon=icon,
                        color=colors.status_completed if ended else color,
                        is_future=not ended,
                        entity_id=p.id,
                    )
                )

        return events

    # ── Financial goal events ─────────────────────────────────

    def _events_from_goals(self, today: datetime.date) -> List[TimelineEvent]:
        goals = self.query(FinancialGoal)
        events: List[TimelineEvent] = []
        cat = CATEGORY_GOAL
        icon = CATEGORY_ICONS[cat]
        color = CATEGORY_COLORS[cat]

        for g in goals:
            if g.is_reached:
                events.append(
                    TimelineEvent(
                        date=g.target_date,
                        title=f"{g.title} reached",
                        description=fmt_currency(g.target_amount),
                        category=cat,
                        icon=ICON_EMOJI_EVENTS_OUTLINED,
                        color=colors.success,
                        is_future=False,
                        entity_id=g.id,
                    )
                )
            else:
                events.append(
                    TimelineEvent(
                        date=g.target_date,
                        title=g.title,
                        description=f"Target: {fmt_currency(g.target_amount)}",
                        category=cat,
                        icon=icon,
                        color=color,
                        is_future=g.target_date > today,
                        entity_id=g.id,
                    )
                )

        return events
