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

            prefix = f"Timesheet-{timesheet.title}"
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
        style = "anvil"
        only_final = False

        result = rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=None,
            document_format=document_format,
            style=style,
            only_final=only_final,
        )

        assert isinstance(result, str)

    def test_creates_only_final_file(self, fake):
        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake)
        document_format = "pdf"
        style = "anvil"
        only_final = True

        with tempfile.TemporaryDirectory() as out_dir:
            rendering.render_invoice(
                user=user,
                invoice=invoice,
                out_dir=out_dir,
                document_format=document_format,
                style=style,
                only_final=only_final,
            )

            prefix = invoice.prefix
            pdf_file = Path(out_dir) / Path(f"{prefix}.pdf")
            assert pdf_file.is_file()

            dir = Path(out_dir) / Path(prefix)
            assert not dir.exists()
