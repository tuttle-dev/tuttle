"""Each sale counts once: reminders and final invoices must not repeat revenue."""

import datetime
from decimal import Decimal

from tuttle import invoicing
from tuttle.forecasting import revenue_series
from tuttle.kpi import compute_kpis
from tuttle.model import Invoice, InvoiceItem
from tuttle.tax_reserves import compute_effective_salary, compute_spendable_income, compute_vat_reserves

from .test_deposit_invoices import _fixed_price_project, _milestones
from .test_tax import _make_invoice


def _reminder(invoice: Invoice, level: int) -> Invoice:
    """A reminder as the app creates one: a copy of the chased invoice's items."""
    reminder = Invoice(
        document_type="reminder",
        date=invoice.date,
        number=invoice.number,
        contract=invoice.contract,
        reminder_level=level,
        paid=invoice.paid,
    )
    reminder.items = [
        InvoiceItem(quantity=item.quantity, unit=item.unit, unit_price=item.unit_price, VAT_rate=item.VAT_rate, description="")
        for item in invoice.items
    ]
    return reminder


def test_reminders_add_no_revenue():
    today = datetime.date.today()
    invoice = _make_invoice(today, [(10, 100, 0.19)], vat_rate=0.19)
    # Paying an invoice marks its whole reminder chain paid.
    chain = [invoice, _reminder(invoice, 1), _reminder(invoice, 2)]

    assert compute_spendable_income(chain, "Germany") == compute_spendable_income([invoice], "Germany")
    assert compute_effective_salary(chain, [], "Germany") == compute_effective_salary([invoice], [], "Germany")
    assert compute_kpis(chain, [], [], country="Germany").total_revenue == Decimal("1190")
    vat = compute_vat_reserves(chain, today, today)
    assert (vat.vat_collected, vat.invoice_count) == (Decimal("190"), 1)


def test_final_invoice_adds_only_what_the_deposits_left():
    today = datetime.date.today()
    project = _fixed_price_project(Decimal("10000"))
    (milestone,) = _milestones(project, "30")
    deposit = invoicing.generate_deposit_invoice(project.contract, project, milestone, number="1", date=today)
    deposit.paid = True
    final = invoicing.generate_final_invoice(project.contract, project, [deposit], number="2", date=today)

    spending = compute_spendable_income([deposit, final], "Germany")

    # The contract is 10,000 net — not the 13,000 that deposit + final state.
    assert spending.gross_revenue_ytd == Decimal("11900.00")
    assert spending.vat_reserve == Decimal("1900.00")
    assert spending.received_gross == Decimal("3570.00")
    assert spending.outstanding_gross == final.remaining_balance


def test_a_reminder_is_not_another_unpaid_invoice():
    today = datetime.date.today()
    invoice = _make_invoice(today, [(10, 100, 0.19)], vat_rate=0.19)
    invoice.paid = False
    chain = [invoice, _reminder(invoice, 1)]

    kpis = compute_kpis(chain, [], [], country="Germany")
    assert (kpis.unpaid_invoices, kpis.outstanding_amount) == (1, Decimal("1190"))
    series = revenue_series(chain, [], None, country="Germany", today=today)
    assert sum(bucket["invoice_count"] for bucket in series["buckets"]) == 1
