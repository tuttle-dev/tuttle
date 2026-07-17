import tempfile
import pytest
from pathlib import Path

import faker

from tuttle import rendering, demo


@pytest.fixture
def fake():
    return faker.Faker()


class TestRenderTimesheet:
    """Tests for render_timesheet"""

    def test_returns_html_when_out_dir_is_none(self, fake):
        user = demo.create_fake_user(fake)
        timesheet = demo.create_fake_timesheet(fake)
        document_format = "html"
        style = "anvil"
        only_final = False

        result = rendering.render_timesheet(
            user=user,
            timesheet=timesheet,
            out_dir=None,
            document_format=document_format,
            style=style,
            only_final=only_final,
        )

        assert isinstance(result, str)

    def test_creates_only_final_file(self, fake):
        user = demo.create_fake_user(fake)
        timesheet = demo.create_fake_timesheet(fake)
        document_format = "pdf"
        style = "anvil"
        only_final = True

        with tempfile.TemporaryDirectory() as out_dir:
            rendering.render_timesheet(
                user=user,
                timesheet=timesheet,
                out_dir=out_dir,
                document_format=document_format,
                style=style,
                only_final=only_final,
            )

            prefix = timesheet.prefix
            pdf_file = Path(out_dir) / Path(f"{prefix}.pdf")
            assert pdf_file.is_file()

            dir = Path(out_dir) / Path(prefix)
            assert not dir.exists()


class TestRenderInvoice:
    """Tests for render_invoice"""

    def test_returns_html_when_out_dir_is_none(self, fake):

        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)
        document_format = "html"
        only_final = False

        result = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format=document_format,
            only_final=only_final,
        )

        assert isinstance(result, str)

    def test_creates_only_final_file(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)
        document_format = "pdf"
        only_final = True

        with tempfile.TemporaryDirectory() as out_dir:
            rendering.render_invoice(
                user=user,
                invoice=invoice,
                out_dir=out_dir,
                document_format=document_format,
                only_final=only_final,
            )

            prefix = invoice.prefix
            pdf_file = Path(out_dir) / Path(f"{prefix}.pdf")
            assert pdf_file.is_file()

            dir = Path(out_dir) / Path(prefix)
            assert not dir.exists()

    def test_due_date_shown_when_enabled(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake, render=False)
        assert invoice.effective_due_date is not None

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            include_due_date=True,
        )

        assert "Due Date" in html
        assert str(invoice.effective_due_date.year) in html

    def test_due_date_hidden_when_disabled(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake, render=False)
        assert invoice.effective_due_date is not None

        html = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format="html",
            include_due_date=False,
        )

        assert "Due Date" not in html


ALL_INVOICE_TEMPLATES = [
    "invoice",
    "invoice-classic",
    "invoice-modern",
    "invoice-bold",
    "invoice-minimal",
    "invoice-anvil",
    "invoice-grayshades",
]

#: invoice-grayshades reports VAT only in the totals block, not per line item.
VAT_COLUMN_TEMPLATES = [t for t in ALL_INVOICE_TEMPLATES if t != "invoice-grayshades"]


def _outside_scope_invoice(fake):
    from decimal import Decimal

    from tuttle.model import TaxCategory

    invoice = demo.create_fake_invoice(fake)
    invoice.contract.VAT_rate = Decimal("0")
    invoice.contract.VAT_category = TaxCategory.outside_scope
    for item in invoice.items:
        item.VAT_rate = Decimal("0")
        item.VAT_category = TaxCategory.outside_scope
    return invoice


def _render(user, invoice, template_name, language="en") -> str:
    return rendering.render_invoice(
        user=user,
        invoice=invoice,
        out_dir=None,
        document_format="html",
        template_name=template_name,
        language=language,
    )


class TestRenderOutsideScopeInvoice:
    """An invoice outside the scope of VAT must not print a 0% VAT rate."""

    @pytest.mark.parametrize("template_name", ALL_INVOICE_TEMPLATES)
    def test_shows_legal_note(self, fake, template_name):
        html = _render(
            demo.create_fake_user(fake), _outside_scope_invoice(fake), template_name
        )
        assert "Not subject to German VAT" in html

    @pytest.mark.parametrize("template_name", ALL_INVOICE_TEMPLATES)
    def test_vat_rate_is_replaced_by_a_dash(self, fake, template_name):
        html = _render(
            demo.create_fake_user(fake), _outside_scope_invoice(fake), template_name
        )
        assert "0.0 %" not in html
        assert "0 %" not in html
        assert "(0%)" not in html
        if template_name in VAT_COLUMN_TEMPLATES:
            assert "&mdash;" in html

    @pytest.mark.parametrize("template_name", VAT_COLUMN_TEMPLATES)
    def test_standard_invoice_keeps_its_vat_rate(self, fake, template_name):
        """Regression guard: the ordinary invoice must be untouched."""
        invoice = demo.create_fake_invoice(fake)
        html = _render(demo.create_fake_user(fake), invoice, template_name)
        assert "Not subject to German VAT" not in html
        assert "&mdash;" not in html

    @pytest.mark.parametrize(
        "language,needle",
        [
            ("en", "§ 3a (2) UStG"),
            ("de", "Nicht steuerbare sonstige Leistung"),
            ("es", "No sujeto al IVA alemán"),
        ],
    )
    def test_note_is_localized(self, fake, language, needle):
        html = _render(
            demo.create_fake_user(fake),
            _outside_scope_invoice(fake),
            "invoice-modern",
            language=language,
        )
        assert needle in html

    def test_renders_a_pdf(self, fake, tmp_path):
        rendering.render_invoice(
            user=demo.create_fake_user(fake),
            invoice=_outside_scope_invoice(fake),
            out_dir=tmp_path,
            document_format="pdf",
            template_name="invoice-modern",
            only_final=True,
        )
        assert list(tmp_path.rglob("*.pdf"))


class TestSellerTaxIdentifierInFooter:
    """EN16931 BR-O-02 bars the VAT number from an outside-scope e-invoice.

    The printed document must not contradict the embedded XML, so it shows the
    tax number (Steuernummer) instead — and nothing when none is set.
    """

    @staticmethod
    def _user(fake, tax_number):
        user = demo.create_fake_user(fake)
        user.VAT_number = "DE123456789"
        user.tax_number = tax_number
        return user

    @pytest.mark.parametrize("template_name", ALL_INVOICE_TEMPLATES)
    def test_standard_invoice_shows_vat_number(self, fake, template_name):
        html = _render(
            self._user(fake, "21/815/08150"),
            demo.create_fake_invoice(fake),
            template_name,
        )
        assert "DE123456789" in html
        assert "21/815/08150" not in html

    @pytest.mark.parametrize("template_name", ALL_INVOICE_TEMPLATES)
    def test_outside_scope_shows_tax_number_not_vat_number(self, fake, template_name):
        html = _render(
            self._user(fake, "21/815/08150"),
            _outside_scope_invoice(fake),
            template_name,
        )
        assert "21/815/08150" in html
        assert "DE123456789" not in html

    @pytest.mark.parametrize("template_name", ALL_INVOICE_TEMPLATES)
    def test_outside_scope_without_tax_number_shows_neither(self, fake, template_name):
        html = _render(
            self._user(fake, None), _outside_scope_invoice(fake), template_name
        )
        assert "DE123456789" not in html

    @pytest.mark.parametrize("template_name", ALL_INVOICE_TEMPLATES)
    def test_standard_invoice_falls_back_to_tax_number_without_vat_number(
        self, fake, template_name
    ):
        """A seller awaiting the USt-IdNr: the printed invoice shows the tax
        number, mirroring the FC identifier embedded in the XML."""
        user = self._user(fake, "21/815/08150")
        user.VAT_number = None
        html = _render(user, demo.create_fake_invoice(fake), template_name)
        assert "21/815/08150" in html

    @pytest.mark.parametrize(
        "language,label",
        [("en", "VAT No."), ("de", "USt-IdNr."), ("es", "N.º IVA")],
    )
    def test_vat_number_label_is_localized(self, fake, language, label):
        html = _render(
            self._user(fake, None),
            demo.create_fake_invoice(fake),
            "invoice-modern",
            language=language,
        )
        assert f"{label}: DE123456789" in html

    @pytest.mark.parametrize(
        "language,label",
        [("en", "Tax No."), ("de", "St.-Nr."), ("es", "N.º fiscal")],
    )
    def test_tax_number_label_is_localized(self, fake, language, label):
        html = _render(
            self._user(fake, "21/815/08150"),
            _outside_scope_invoice(fake),
            "invoice-modern",
            language=language,
        )
        assert f"{label}: 21/815/08150" in html
