"""Deposit (Abschlagsrechnung) and final (Schlussrechnung) invoices.

The settlement arithmetic is the part with legal weight: a Schlussrechnung
states the full contract amount with its VAT and then deducts the *gross*
amounts already invoiced as deposits. Getting that wrong overstates what the
client owes, so it is pinned down here with the worked example from issue #326.
"""

import datetime
from decimal import Decimal

import pytest

from tuttle import invoicing
from tuttle.app.contracts.intent import ContractsIntent
from tuttle.einvoice import unsupported_reason
from tuttle.model import (
    Address,
    Client,
    Contract,
    Invoice,
    PaymentMilestone,
    Project,
    TaxCategory,
)
from tuttle.time import ContractType, Cycle

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _fixed_price_project(fixed_price: Decimal, tag: str = "#deposit") -> Project:
    client = Client(
        name="Sam Lowry",
        address=Address(
            street="Shangrila Towers",
            number="1",
            postal_code="00000",
            city="Brazil",
            country="Germany",
        ),
    )
    contract = Contract(
        title="Central Heating Overhaul",
        client=client,
        start_date=datetime.date(2026, 1, 10),
        type=ContractType.fixed_price,
        fixed_price=fixed_price,
        currency="EUR",
        VAT_rate=Decimal("0.19"),
        billing_cycle=Cycle.monthly,
    )
    return Project(
        title="Heating Overhaul",
        description="Ductwork",
        tag=tag,
        contract=contract,
        start_date=datetime.date(2026, 1, 10),
        end_date=datetime.date(2026, 6, 30),
    )


def _milestones(project: Project, *percentages: str) -> list[PaymentMilestone]:
    schedule = [
        PaymentMilestone(
            title=f"Instalment {position + 1}",
            percentage=Decimal(pct),
            position=position,
            contract=project.contract,
        )
        for position, pct in enumerate(percentages)
    ]
    project.contract.payment_milestones = schedule
    return schedule


def _settlement(fixed_price: str, *percentages: str) -> tuple[list[Invoice], Invoice]:
    """Issue a deposit per milestone, then the final invoice deducting them."""
    project = _fixed_price_project(Decimal(fixed_price))
    schedule = _milestones(project, *percentages)
    deposits = [
        invoicing.generate_deposit_invoice(
            contract=project.contract,
            project=project,
            milestone=milestone,
            number=f"2026-{position + 1:03d}",
            date=datetime.date(2026, 1, 15),
        )
        for position, milestone in enumerate(schedule)
    ]
    final = invoicing.generate_final_invoice(
        contract=project.contract,
        project=project,
        deposit_invoices=deposits,
        number="2026-999",
        date=datetime.date(2026, 6, 30),
    )
    return deposits, final


# ---------------------------------------------------------------------------
# Settlement arithmetic
# ---------------------------------------------------------------------------


class TestSettlementMath:
    """The worked example from issue #326: 10,000 net at 19% VAT, 50/50."""

    def test_deposit_bills_its_share_of_the_contract(self):
        deposits, _ = _settlement("10000", "50", "50")
        assert deposits[0].sum == Decimal("5000.00")
        assert deposits[0].VAT_total == Decimal("950.00")
        assert deposits[0].total == Decimal("5950.00")

    def test_final_invoice_states_the_whole_contract(self):
        _, final = _settlement("10000", "50", "50")
        assert final.sum == Decimal("10000")
        assert final.VAT_total == Decimal("1900.00")
        assert final.total == Decimal("11900.00")

    def test_deductions_carry_gross_and_the_vat_within(self):
        deposits, final = _settlement("10000", "50", "50")
        assert final.deposit_deductions == [
            {
                "invoice_number": deposits[0].number,
                "gross": Decimal("5950.00"),
                "vat": Decimal("950.00"),
                "net": Decimal("5000.00"),
            },
            {
                "invoice_number": deposits[1].number,
                "gross": Decimal("5950.00"),
                "vat": Decimal("950.00"),
                "net": Decimal("5000.00"),
            },
        ]

    def test_remaining_balance_is_the_total_less_the_deposits(self):
        deposits, final = _settlement("10000", "50", "50")
        final.deposits = deposits[:1]
        assert final.remaining_balance == Decimal("5950.00")

    def test_a_fully_deposited_contract_leaves_nothing_to_pay(self):
        _, final = _settlement("10000", "50", "50")
        assert final.remaining_balance == Decimal("0.00")

    def test_thirds_round_to_cents_and_the_settlement_absorbs_the_rest(self):
        """A schedule of thirds bills 3,333.33 three times; the last cent of
        the contract total surfaces as remaining balance on the settlement."""
        deposits, final = _settlement("10000", "33.34", "33.33", "33.33")
        assert [d.sum for d in deposits] == [
            Decimal("3334.00"),
            Decimal("3333.00"),
            Decimal("3333.00"),
        ]
        assert final.remaining_balance == Decimal("0.00")

    def test_deposit_inherits_the_contracts_tax_treatment(self):
        deposits, final = _settlement("10000", "100")
        assert deposits[0].items[0].VAT_category is TaxCategory.standard
        assert final.items[0].VAT_category is TaxCategory.standard

    def test_deposit_links_to_its_milestone_and_the_settlement(self):
        deposits, final = _settlement("10000", "50", "50")
        assert all(d.is_deposit for d in deposits)
        assert final.is_final_invoice
        assert final.deposits == deposits

    def test_an_ordinary_invoice_owes_its_full_total(self):
        """`remaining_balance` is the amount due on every document type, so a
        template can print it unconditionally."""
        project = _fixed_price_project(Decimal("1000"))
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="2026-001",
            date=datetime.date(2026, 2, 1),
        )
        assert not invoice.is_deposit and not invoice.is_final_invoice
        assert invoice.remaining_balance == invoice.total == Decimal("1190.00")

    @pytest.mark.parametrize("kind", ["deposit", "final"])
    def test_a_time_based_contract_cannot_be_settled_in_instalments(self, kind):
        project = _fixed_price_project(Decimal("10000"))
        project.contract.fixed_price = None
        milestone = _milestones(project, "100")[0]
        with pytest.raises(ValueError):
            if kind == "deposit":
                invoicing.generate_deposit_invoice(
                    contract=project.contract,
                    project=project,
                    milestone=milestone,
                    number="2026-001",
                )
            else:
                invoicing.generate_final_invoice(
                    contract=project.contract,
                    project=project,
                    deposit_invoices=[],
                    number="2026-001",
                )


# ---------------------------------------------------------------------------
# Payment schedule validation
# ---------------------------------------------------------------------------


def _row(title="Instalment", percentage=None, amount=None, existing=None, position=0):
    return {
        "existing": existing,
        "title": title,
        "percentage": Decimal(percentage) if percentage is not None else None,
        "amount": Decimal(amount) if amount is not None else None,
        "position": position,
    }


def _validate(contract, rows, existing=()):
    existing_by_id = {m.id: m for m in existing}
    incoming_ids = {row["existing"].id for row in rows if row["existing"] is not None}
    return ContractsIntent._validate_milestone_schedule(contract, rows, existing_by_id, incoming_ids)


class TestMilestoneScheduleValidation:
    """A schedule that does not add up to the contract would mis-bill."""

    @pytest.fixture
    def contract(self):
        return _fixed_price_project(Decimal("10000")).contract

    def test_percentages_summing_to_100_are_accepted(self, contract):
        rows = [_row(percentage="40"), _row(percentage="60", position=1)]
        assert _validate(contract, rows) is None

    def test_percentages_must_sum_to_100(self, contract):
        rows = [_row(percentage="40"), _row(percentage="40", position=1)]
        assert "sum to 100%" in _validate(contract, rows)

    def test_amounts_must_sum_to_the_fixed_price(self, contract):
        rows = [_row(amount="4000"), _row(amount="4000", position=1)]
        assert "sum to the contract fixed price" in _validate(contract, rows)

    def test_amounts_summing_to_the_fixed_price_are_accepted(self, contract):
        rows = [_row(amount="4000"), _row(amount="6000", position=1)]
        assert _validate(contract, rows) is None

    def test_amounts_need_a_fixed_price_to_check_against(self, contract):
        contract.fixed_price = None
        rows = [_row(amount="4000"), _row(amount="6000", position=1)]
        assert "require a fixed-price contract" in _validate(contract, rows)

    def test_percentages_and_amounts_cannot_be_mixed(self, contract):
        rows = [_row(percentage="50"), _row(amount="5000", position=1)]
        assert "either a percentage or an amount" in _validate(contract, rows)

    def test_a_schedule_needs_titles(self, contract):
        rows = [_row(title="", percentage="50"), _row(title=" ", percentage="50", position=1)]
        assert "needs a title" in _validate(contract, rows)

    def test_an_empty_schedule_clears_the_contract(self, contract):
        assert _validate(contract, []) is None

    def test_an_invoiced_milestone_cannot_be_removed(self, contract):
        invoiced = PaymentMilestone(id=1, title="Upfront", percentage=Decimal("50"), position=0, invoiced=True)
        rows = [_row(percentage="100")]
        assert "already been invoiced" in _validate(contract, rows, existing=[invoiced])

    def test_an_invoiced_milestone_cannot_be_repriced(self, contract):
        invoiced = PaymentMilestone(id=1, title="Upfront", percentage=Decimal("50"), position=0, invoiced=True)
        rows = [
            _row(percentage="70", existing=invoiced),
            _row(percentage="30", position=1),
        ]
        assert "Cannot change the amount" in _validate(contract, rows, existing=[invoiced])

    def test_an_invoiced_milestone_may_be_kept_unchanged(self, contract):
        invoiced = PaymentMilestone(id=1, title="Upfront", percentage=Decimal("50"), position=0, invoiced=True)
        rows = [
            _row(title="Upfront", percentage="50", existing=invoiced),
            _row(percentage="50", position=1),
        ]
        assert _validate(contract, rows, existing=[invoiced]) is None


# ---------------------------------------------------------------------------
# E-invoicing guard
# ---------------------------------------------------------------------------


class TestEInvoiceGuard:
    """Tuttle writes type code 380 with full totals, which misstates an
    instalment; deposits and settlements therefore ship as PDF only."""

    def test_a_deposit_is_not_embedded(self):
        deposits, _ = _settlement("10000", "50", "50")
        assert "prepayment type code" in unsupported_reason(deposits[0])

    def test_a_final_invoice_is_not_embedded(self):
        _, final = _settlement("10000", "50", "50")
        assert "prepaid-amount settlement" in unsupported_reason(final)

    def test_an_ordinary_invoice_is_embedded(self):
        project = _fixed_price_project(Decimal("1000"))
        invoice = invoicing.generate_fixed_price_invoice(
            contract=project.contract,
            project=project,
            number="2026-001",
            date=datetime.date(2026, 2, 1),
        )
        assert unsupported_reason(invoice) is None

    def test_embedding_a_deposit_is_refused_outright(self, tmp_path):
        """The guard also protects direct callers of the einvoice module."""
        from tuttle.einvoice import embed_zugferd_in_pdf
        from tuttle.model import User

        deposits, _ = _settlement("10000", "50", "50")
        pdf = tmp_path / "deposit.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        with pytest.raises(ValueError, match="Cannot embed e-invoice XML"):
            embed_zugferd_in_pdf(pdf_path=str(pdf), invoice=deposits[0], user=User(name="Harry Tuttle"))
