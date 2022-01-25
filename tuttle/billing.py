"""Module combining functions required for billing."""

from .model import User, Project
from . import timetracking, invoice, rendering


def billing(
    user: User,
    project: Project,
    period,
    timetracking_source,
    out_dir=None,
):
    """Convenience function for Timesheet and Invoice generation and rendering."""
    the_timesheet = timetracking.generate_timesheet(
        source=timetracking_source,
        project=project,
        period=period,
    )

    the_invoice = invoice.generate_invoice(
        timesheets=[
            the_timesheet,
        ],
        contract=project.contract,
    )

    rendering.render_invoice(user=user, invoice=the_invoice, out_dir=out_dir)

    rendering.render_timesheet(user=user, invoice=the_invoice, out_dir=out_dir)
