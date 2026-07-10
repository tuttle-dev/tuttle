import locale
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

    def test_writes_non_ascii_content_regardless_of_locale_encoding(
        self, fake, monkeypatch
    ):
        """Regression test for #402.

        `render_timesheet` used to open the output file without an explicit
        encoding, so the write picked up the platform's preferred locale
        encoding (e.g. cp1252 on Windows) and raised a UnicodeEncodeError for
        any non-ASCII characters. Force a non-UTF-8 preferred encoding here to
        simulate that environment and confirm the write now always uses
        UTF-8.
        """
        monkeypatch.setattr(
            locale, "getpreferredencoding", lambda do_setlocale=True: "cp1252"
        )

        user = demo.create_fake_user(fake)
        timesheet = demo.create_fake_timesheet(fake)
        timesheet.title = "Zeiterfassung – 日本語 – café ☕"

        with tempfile.TemporaryDirectory() as out_dir:
            rendering.render_timesheet(
                user=user,
                timesheet=timesheet,
                out_dir=out_dir,
                document_format="html",
                style="anvil",
                only_final=False,
            )

            html_path = Path(out_dir) / timesheet.prefix / f"{timesheet.prefix}.html"
            assert html_path.is_file()
            content = html_path.read_text(encoding="utf-8")
            assert "日本語" in content


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

    def test_writes_non_ascii_content_regardless_of_locale_encoding(
        self, fake, monkeypatch
    ):
        """Regression test for #402.

        `render_invoice` used to open the output file without an explicit
        encoding, so the write picked up the platform's preferred locale
        encoding (e.g. cp1252 on Windows) and raised a UnicodeEncodeError for
        any non-ASCII characters. Force a non-UTF-8 preferred encoding here to
        simulate that environment and confirm the write now always uses
        UTF-8.
        """
        monkeypatch.setattr(
            locale, "getpreferredencoding", lambda do_setlocale=True: "cp1252"
        )

        user = demo.create_fake_user(fake)
        invoice = demo.create_fake_invoice(fake, render=False)
        invoice.notes = "Vielen Dank – 日本語 – café ☕"

        with tempfile.TemporaryDirectory() as out_dir:
            rendering.render_invoice(
                user=user,
                invoice=invoice,
                out_dir=out_dir,
                document_format="html",
                only_final=False,
            )

            html_path = Path(out_dir) / invoice.prefix / f"{invoice.prefix}.html"
            assert html_path.is_file()
            content = html_path.read_text(encoding="utf-8")
            assert "日本語" in content

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
