"""Document rendering."""

import base64
import glob
import io
import shutil
from pathlib import Path
from typing import Optional

import jinja2
import pandas
import PyPDF2
from babel.dates import format_date
from babel.numbers import format_currency
from loguru import logger
from segno.helpers import make_epc_qr

from .model import BankAccount, Invoice, Timesheet, User

LANGUAGE_TO_LOCALE = {
    "en": "en_US",
    "de": "de_DE",
    "es": "es_ES",
}

INVOICE_LABELS = {
    "en": {
        "invoice": "Invoice",
        "invoice_no": "Invoice No.",
        "date": "Date",
        "due_date": "Due Date",
        "bill_to": "Bill To",
        "from": "From",
        "billed_to": "Billed to",
        "qty": "Qty",
        "unit": "Unit",
        "unit_price": "Unit Price",
        "vat": "VAT",
        "vat_number": "VAT No.",
        "tax_number": "Tax No.",
        "subtotal": "Subtotal",
        "total_due": "Total Due",
        "payment": "Payment",
        "payment_details": "Payment Details",
        "account_holder": "Account",
        "description": "Description",
        "closing": "Thank you for your business.",
        "outside_scope_note": (
            "Not subject to German VAT — the place of supply is the recipient's "
            "country (§ 3a (2) UStG / Art. 44 VAT Directive)."
        ),
        "reminder": "Payment Reminder",
        "reminder_n": "{n}. Payment Reminder",
        "reminder_fee": "Reminder Fee",
        "original_invoice": "Original Invoice",
        "document_type": "Document type",
        "reminder_closing": "Please settle the outstanding amount by the new due date.",
        "deposit_invoice": "Deposit Invoice",
        "final_invoice": "Final Invoice",
        "total_fee": "Total fee",
        "less_deposit": "less deposit per invoice no.",
        "vat_included_therein": "VAT included therein",
        "remaining_balance": "Remaining balance",
        "gross": "Gross",
        "deposit_due": "Deposit due",
        "in_respect_of": "In respect of",
        "payment_milestone": "Payment milestone",
        "contract_total": "Contract total",
        "deposit_closing": "This is a partial payment (deposit invoice) towards the contract total.",
        "units": {
            "hour": ("hour", "hours"),
            "day": ("day", "days"),
            "fixed_price": ("fixed price", "fixed price"),
        },
    },
    "de": {
        "invoice": "Rechnung",
        "invoice_no": "Rechnung Nr.",
        "date": "Datum",
        "due_date": "Fälligkeitsdatum",
        "bill_to": "Rechnungsempfänger",
        "from": "Von",
        "billed_to": "Rechnungsempfänger",
        "qty": "Menge",
        "unit": "Einheit",
        "unit_price": "Einzelpreis",
        "vat": "USt.",
        "vat_number": "USt-IdNr.",
        "tax_number": "St.-Nr.",
        "subtotal": "Zwischensumme",
        "total_due": "Gesamtbetrag",
        "payment": "Zahlung",
        "payment_details": "Zahlungsdetails",
        "account_holder": "Konto",
        "description": "Beschreibung",
        "closing": "Vielen Dank für Ihren Auftrag.",
        "outside_scope_note": (
            "Nicht steuerbare sonstige Leistung — Leistungsort im Ausland gemäß § 3a Abs. 2 UStG / Art. 44 MwStSystRL."
        ),
        "reminder": "Zahlungserinnerung",
        "reminder_n": "{n}. Mahnung",
        "reminder_fee": "Mahngebühr",
        "original_invoice": "Ursprungsrechnung",
        "document_type": "Belegart",
        "reminder_closing": "Bitte begleichen Sie den offenen Betrag bis zum neuen Fälligkeitsdatum.",
        "deposit_invoice": "Abschlagsrechnung",
        "final_invoice": "Schlussrechnung",
        "total_fee": "Gesamthonorar",
        "less_deposit": "abzgl. Abschlag lt. Rechnung Nr.",
        "vat_included_therein": "darin enthaltene USt.",
        "remaining_balance": "Restbetrag",
        "gross": "Brutto",
        "deposit_due": "Abschlagsbetrag",
        "in_respect_of": "Betreffend",
        "payment_milestone": "Zahlungsmeilenstein",
        "contract_total": "Vertragsgesamtbetrag",
        "deposit_closing": "Dies ist eine Teilzahlung (Abschlagsrechnung) auf den Vertragsgesamtbetrag.",
        "units": {
            "hour": ("Stunde", "Stunden"),
            "day": ("Tag", "Tage"),
            "fixed_price": ("pauschal", "pauschal"),
        },
    },
    "es": {
        "invoice": "Factura",
        "invoice_no": "N.º de factura",
        "date": "Fecha",
        "due_date": "Fecha de vencimiento",
        "bill_to": "Facturar a",
        "from": "De",
        "billed_to": "Facturar a",
        "qty": "Cant.",
        "unit": "Unidad",
        "unit_price": "Precio unit.",
        "vat": "IVA",
        "vat_number": "N.º IVA",
        "tax_number": "N.º fiscal",
        "subtotal": "Subtotal",
        "total_due": "Total a pagar",
        "payment": "Pago",
        "payment_details": "Datos de pago",
        "account_holder": "Titular",
        "description": "Descripción",
        "closing": "Gracias por su confianza.",
        "outside_scope_note": (
            "No sujeto al IVA alemán — el lugar de prestación es el país del destinatario (art. 44 de la Directiva del IVA)."
        ),
        "reminder": "Recordatorio de pago",
        "reminder_n": "{n}.º recordatorio de pago",
        "reminder_fee": "Cargo por recordatorio",
        "original_invoice": "Factura original",
        "document_type": "Tipo de documento",
        "reminder_closing": "Le rogamos abone el importe pendiente antes de la nueva fecha de vencimiento.",
        "deposit_invoice": "Factura de anticipo",
        "final_invoice": "Factura final",
        "total_fee": "Honorario total",
        "less_deposit": "menos anticipo según factura n.º",
        "vat_included_therein": "IVA incluido",
        "remaining_balance": "Saldo pendiente",
        "gross": "Bruto",
        "deposit_due": "Anticipo a pagar",
        "in_respect_of": "Referente a",
        "payment_milestone": "Hito de pago",
        "contract_total": "Importe total del contrato",
        "deposit_closing": "Este documento es un pago parcial (factura de anticipo) sobre el importe total del contrato.",
        "units": {
            "hour": ("hora", "horas"),
            "day": ("día", "días"),
            "fixed_price": ("precio fijo", "precio fijo"),
        },
    },
}


def get_template_path(template_name) -> str:
    """Get the path to an HTML template by name"""
    app_dir = Path(__file__).parent.parent.resolve()
    template_path = app_dir / Path(f"templates/{template_name}")
    logger.info(f"Template path: {template_path}")
    return template_path


def get_shared_template_path() -> Path:
    """Directory of partials and stylesheets every document template shares.

    Lets the templates import one definition of the parts that must not drift
    between skins — notably the deposit/final settlement layout, where the
    markup carries the legal statement of what has been deducted.
    """
    return Path(__file__).parent.parent.resolve() / "templates" / "_shared"


def convert_html_to_pdf(
    in_path,
    out_path,
    css_paths=[],
):
    """Convert an HTML file to PDF using plutoprint.

    CSS is resolved automatically from <link> tags in the HTML via
    the file:// URL.  The *css_paths* parameter is accepted for
    interface compatibility but ignored.
    """
    logger.info(f"converting html to pdf: {in_path} -> {out_path}")
    import plutoprint

    book = plutoprint.Book(plutoprint.PAGE_SIZE_A4)
    book.load_url(Path(in_path).resolve().as_uri())
    book.write_to_pdf(str(out_path))


def generate_payment_qr(bank_account: Optional[BankAccount], invoice: Invoice) -> Optional[str]:
    """Generate a SEPA payment (EPC/Girocode) QR code for an invoice, if eligible.

    Returns an SVG data URI, or None if ``bank_account`` is missing or incomplete,
    or the invoice isn't in EUR (the EPC QR format is SEPA-only).
    """
    if bank_account is None or not (bank_account.BIC and bank_account.IBAN and bank_account.name):
        return None
    if invoice.currency != "EUR":
        return None

    try:
        qr = make_epc_qr(
            name=bank_account.name,
            iban=bank_account.IBAN,
            amount=float(invoice.total),
            text=invoice.number,
            bic=bank_account.BIC,
        )
    except ValueError as ex:
        logger.warning(f"Could not generate payment QR code for invoice {invoice.number}: {ex}")
        return None

    return qr.svg_data_uri(scale=4)


def render_invoice(
    user: User,
    invoice: Invoice,
    out_dir,
    document_format: str = "pdf",
    template_name: str = "invoice-modern",
    only_final: bool = False,
    language: str = "en",
    e_invoice_profile: Optional[str] = None,
    include_logo: bool = True,
    include_due_date: bool = True,
    include_signature: bool = True,
    include_qr_code: bool = False,
    accent_color: Optional[str] = None,
):
    """Render an Invoice using an HTML template.

    Args:
        user: The freelancer / app user.
        invoice: The invoice to render.
        out_dir: Output directory. If None, returns the raw HTML string.
        document_format: "pdf" or "html".
        template_name: Directory name under templates/ (e.g. "invoice-modern").
        only_final: Keep only the final output file and remove intermediates.
        language: Language code for labels and date/currency formatting ("en", "de", "es").
        e_invoice_profile: If set, embed ZUGFeRD/Factur-X XML into the PDF.
            One of "EN16931", "EXTENDED", "BASIC", "MINIMUM", "XRECHNUNG", or None.
        include_qr_code: Whether to render a SEPA payment (EPC/Girocode) QR code in the
            payment section, when the invoice is in EUR and a complete bank account is set.
        accent_color: Hex color string (e.g. "#C8281E") to use as the invoice accent color.
            Falls back to the template's hardcoded default when None or empty.
    """
    babel_locale = LANGUAGE_TO_LOCALE.get(language, "en_US")
    labels = INVOICE_LABELS.get(language, INVOICE_LABELS["en"])

    def as_currency(number):
        return format_currency(number, currency=invoice.contract.currency, locale=babel_locale)

    def as_date(d):
        if d is None:
            return ""
        return format_date(d, format="long", locale=babel_locale)

    def as_date_short(d):
        if d is None:
            return ""
        return format_date(d, format="medium", locale=babel_locale)

    def as_percentage(number):
        return f"{number * 100:.1f} %"

    def unit_label(raw_unit, quantity=None):
        """Translate a TimeUnit value (e.g. "hour", "day") into the active language.

        When ``quantity`` is given, choose between singular and plural form.
        Unknown units pass through unchanged.
        """
        units = labels.get("units", {})
        normalized = raw_unit.replace(" ", "_")
        forms = units.get(normalized)
        if not forms:
            return raw_unit
        singular, plural = forms
        if quantity is None:
            return singular
        try:
            q = float(quantity)
        except (TypeError, ValueError):
            return singular
        return singular if abs(q - 1) < 1e-9 else plural

    template_path = get_template_path(template_name)
    shared_path = get_shared_template_path()
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader([template_path, shared_path]))

    template_env.filters["as_currency"] = as_currency
    template_env.filters["as_date"] = as_date
    template_env.filters["as_date_short"] = as_date_short
    template_env.filters["as_percentage"] = as_percentage
    template_env.filters["unit_label"] = unit_label

    is_reminder = getattr(invoice, "is_reminder", False)
    reminder_title = ""
    if is_reminder:
        n = getattr(invoice, "reminder_level", 1)
        tpl = labels.get("reminder_n", "{n}. Payment Reminder")
        reminder_title = tpl.format(n=n)

    # Mirror the XML (einvoice.py): VAT number when it may appear and is set,
    # else the tax number, else nothing.
    if not invoice.is_outside_scope and user.VAT_number:
        seller_tax_id_label = labels.get("vat_number", "VAT No.")
        seller_tax_id = user.VAT_number
    else:
        seller_tax_id_label = labels.get("tax_number", "Tax No.")
        seller_tax_id = user.tax_number or ""

    # The bank account named on the contract takes precedence; without one the
    # user's default account is used.
    payee_account = (invoice.contract.bank_account if invoice.contract else None) or user.bank_account
    qr_code_data_uri = generate_payment_qr(payee_account, invoice) if include_qr_code else None

    # Deposit and final invoices are the two halves of one settlement: the
    # deposit states what share of the contract it bills, the final states the
    # whole contract and deducts every deposit already issued. Both need the
    # invoice fully hydrated — callers render from a session-loaded instance.
    is_deposit = invoice.is_deposit
    is_final = invoice.is_final_invoice
    deposit_deductions = invoice.deposit_deductions
    remaining_balance = invoice.remaining_balance

    contract_title = ""
    contract_total = None
    milestone_title = ""
    milestone_percentage = None
    if invoice.contract:
        contract_title = invoice.contract.title or ""
        contract_total = invoice.contract.fixed_price
    if is_deposit and invoice.milestone is not None:
        milestone_title = invoice.milestone.title or ""
        milestone_percentage = invoice.milestone.percentage

    invoice_template = template_env.get_template("invoice.html")
    html = invoice_template.render(
        user=user,
        invoice=invoice,
        l=labels,
        seller_tax_id=seller_tax_id,
        seller_tax_id_label=seller_tax_id_label,
        is_reminder=is_reminder,
        reminder_title=reminder_title,
        is_deposit=is_deposit,
        is_final=is_final,
        deposit_deductions=deposit_deductions,
        remaining_balance=remaining_balance,
        contract_title=contract_title,
        contract_total=contract_total,
        milestone_title=milestone_title,
        milestone_percentage=milestone_percentage,
        notes=invoice.notes,
        include_logo=include_logo,
        include_due_date=include_due_date,
        include_signature=include_signature,
        qr_code_data_uri=qr_code_data_uri,
        accent_color=accent_color or "",
        bank_account=payee_account,
    )
    if out_dir is None:
        return html

    invoice_dir = Path(out_dir) / Path(invoice.prefix)
    invoice_dir.mkdir(parents=True, exist_ok=True)
    invoice_path = invoice_dir / Path(f"{invoice.prefix}.html")
    with open(invoice_path, "w", encoding="utf-8") as invoice_file:
        invoice_file.write(html)

    # Copy all CSS files and subdirectories from the template. Shared
    # stylesheets go first so a template's own rules can override them.
    for css in shared_path.glob("*.css"):
        shutil.copy(css, invoice_dir / css.name)
    for item in template_path.iterdir():
        dest = invoice_dir / item.name
        if item.is_file() and item.suffix == ".css":
            shutil.copy(item, dest)
        elif item.is_dir() and not item.name.startswith("."):
            shutil.copytree(item, dest, dirs_exist_ok=True)

    if document_format == "pdf":
        css_paths = [path for path in glob.glob(f"{invoice_dir}/**/*.css", recursive=True)]
        pdf_out = invoice_dir / Path(f"{invoice.prefix}.pdf")
        convert_html_to_pdf(
            in_path=str(invoice_path),
            css_paths=css_paths,
            out_path=pdf_out,
        )
        if e_invoice_profile:
            from .einvoice import embed_zugferd_in_pdf, unsupported_reason

            reason = unsupported_reason(invoice)
            if reason:
                logger.warning(
                    f"Skipping e-invoice XML for {invoice.number or invoice.id}: {reason}. "
                    "The PDF is written without embedded XML."
                )
            else:
                embed_zugferd_in_pdf(
                    pdf_path=str(pdf_out),
                    invoice=invoice,
                    user=user,
                    profile=e_invoice_profile,
                )
    if only_final:
        final_output_path = out_dir / Path(f"{invoice.prefix}.{document_format}")
        if document_format == "pdf":
            shutil.move(invoice_dir / Path(f"{invoice.prefix}.pdf"), final_output_path)
        else:
            shutil.move(invoice_dir / Path(f"{invoice.prefix}.html"), final_output_path)
        shutil.rmtree(invoice_dir)
    invoice.rendered = True


def render_timesheet(
    user: User,
    timesheet: Timesheet,
    out_dir,
    document_format: str = "pdf",
    style: str = "anvil",
    only_final: bool = False,
):
    """Render a Timeseheet using an HTML template.

    Args:
        user (User): [description]
        timesheet (Timesheet): [description]
        out_dir (str, optional): [description]. Defaults to None.

    Returns:
        str: [description]
    """
    template_name = "timesheet-anvil"
    template_path = get_template_path(template_name)
    template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_path))
    # filters
    template_env.filters["as_hours"] = lambda td: td / pandas.Timedelta("1 hour")
    template_env.filters["date"] = lambda dt: dt.strftime("%Y-%m-%d") if dt else ""
    template_env.filters["time"] = lambda dt: dt.strftime("%H:%M") if dt else ""
    template_env.filters["datetime"] = lambda dt: dt.strftime("%Y-%m-%d %H:%M") if dt else ""
    template_env.filters["hours_minutes"] = lambda td: (
        f"{int(td.total_seconds() // 3600)}:{int((td.total_seconds() % 3600) // 60):02d}" if td else ""
    )

    def _is_all_day(item) -> bool:
        """A calendar event is all-day if it starts at midnight and lasts a multiple of 24h."""
        if not item.begin or not item.end:
            return False
        if item.begin.hour or item.begin.minute or item.begin.second:
            return False
        total = (item.end - item.begin).total_seconds()
        return total > 0 and total % 86400 == 0

    def _time_range(item) -> str:
        if _is_all_day(item):
            return "All day"
        return f"{item.begin.strftime('%H:%M')} – {item.end.strftime('%H:%M')}"

    def _clean_title(item) -> str:
        """Calendar event title with the project tag stripped, falling back to description."""
        title = (item.title or "").replace(item.tag or "", "").strip(" -–·:|")
        if not title:
            return (item.description or "").strip()
        return title

    def _clean_notes(item) -> str:
        """Return description only when it adds information beyond the title."""
        desc = (item.description or "").strip()
        if not desc:
            return ""
        title_raw = (item.title or "").strip()
        title_clean = _clean_title(item)
        if desc == title_raw or desc == title_clean:
            return ""
        return desc

    template_env.filters["time_range"] = _time_range
    template_env.filters["clean_title"] = _clean_title
    template_env.filters["clean_notes"] = _clean_notes

    timesheet_template = template_env.get_template("timesheet.html")
    html = timesheet_template.render(user=user, timesheet=timesheet, style=style)
    # output
    if out_dir is None:
        return html
    else:
        # write invoice html
        prefix = timesheet.prefix
        timesheet_dir = Path(out_dir) / Path(prefix)
        timesheet_dir.mkdir(parents=True, exist_ok=True)
        timesheet_path = timesheet_dir / Path(f"{prefix}.html")
        with open(timesheet_path, "w", encoding="utf-8") as timesheet_file:
            timesheet_file.write(html)
        # copy stylsheets
        if style:
            stylesheets = []
            stylesheet_folders = []
            if style == "anvil":
                stylesheets = ["timesheet.css"]
                stylesheet_folders = [
                    "web",
                ]
            for stylesheet_path in stylesheets:
                stylesheet_path = template_path / stylesheet_path
                shutil.copy(stylesheet_path, timesheet_dir)
            for stylesheet_folder_path in stylesheet_folders:
                full_stylesheet_folder_path = template_path / stylesheet_folder_path
                shutil.copytree(
                    full_stylesheet_folder_path,
                    timesheet_dir / stylesheet_folder_path,
                    dirs_exist_ok=True,
                )
        if document_format == "pdf":
            css_paths = [path for path in glob.glob(f"{timesheet_dir}/**/*.css", recursive=True)]
            convert_html_to_pdf(
                in_path=str(timesheet_path),
                css_paths=css_paths,
                out_path=timesheet_dir / Path(f"{prefix}.pdf"),
            )
        if only_final:
            final_output_path = out_dir / Path(f"{prefix}.{document_format}")
            if document_format == "pdf":
                shutil.move(timesheet_dir / Path(f"{prefix}.pdf"), final_output_path)
            else:
                shutil.move(timesheet_dir / Path(f"{prefix}.html"), final_output_path)
            shutil.rmtree(timesheet_dir)
    # finally set the rendered flag
    timesheet.rendered = True


def generate_document_thumbnail(pdf_path: str, thumbnail_width: int) -> str:
    """
    Generate a thumbnail image of a PDF document.

    Parameters:
        pdf_path (str): The path to the PDF file.
        thumbnail_width (int): The width of the thumbnail image in pixels.

    Returns:
        str: A base64-encoded string of the thumbnail image.
    """
    # Open the PDF file in memory
    with open(pdf_path, "rb") as pdf_file:
        # Create a PDF object
        pdf_doc = PyPDF2.PdfFileReader(pdf_file)

        # Get the first page
        page = pdf_doc.getPage(0)

        # Get the size of the page
        page_width, page_height = page.mediaBox.upperRight

        # Calculate the aspect ratio of the page
        aspect_ratio = page_width / page_height

        # Calculate the size of the thumbnail image
        thumbnail_height = thumbnail_width / aspect_ratio
        thumbnail_size = (thumbnail_width, thumbnail_height)

        # Generate a thumbnail image
        image = page.thumbnail(thumbnail_size)

        # Save the image to a BytesIO object
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="JPEG")

        # Get the contents of the BytesIO object as a string
        image_data = img_buffer.getvalue()

        # Encode the image data as base64
        base64_image = base64.b64encode(image_data).decode()

    return base64_image
