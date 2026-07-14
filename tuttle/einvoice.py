"""Electronic invoice generation via ZUGFeRD / Factur-X (python-drafthorse)."""

from datetime import timedelta, timezone, datetime
from decimal import Decimal

import pycountry
from loguru import logger

from drafthorse.models.accounting import ApplicableTradeTax
from drafthorse.models.document import Document
from drafthorse.models.party import TaxRegistration
from drafthorse.models.payment import PaymentMeans, PaymentTerms
from drafthorse.models.tradelines import LineItem
from drafthorse.pdf import attach_xml

from .fx import convert
from .model import Invoice, TaxCategory, User, normalize_tax_category
from .tax import get_tax_system

# -- Helpers ------------------------------------------------------------------

UNIT_CODE_MAP = {
    "hour": "HUR",
    "day": "DAY",
    "month": "MON",
    "unit": "C62",
    "piece": "C62",
    "minute": "MIN",
}


def unit_to_unece(unit: str) -> str:
    """Map Tuttle time-unit strings to UN/ECE Recommendation 20 codes."""
    key = unit.lower().rstrip("s")
    code = UNIT_CODE_MAP.get(key)
    if code is None:
        logger.warning(f"Unknown unit '{unit}', falling back to C62 (unit)")
        return "C62"
    return code


def country_to_iso(name: str) -> str:
    """Convert a country name to its ISO 3166-1 alpha-2 code.

    Handles common names like "Germany" -> "DE" via pycountry fuzzy search.
    If already a 2-letter code, returns it directly.
    """
    if not name:
        return "DE"
    name = name.strip()
    if len(name) == 2 and name.isalpha():
        return name.upper()
    try:
        result = pycountry.countries.lookup(name)
        return result.alpha_2
    except LookupError:
        try:
            results = pycountry.countries.search_fuzzy(name)
            if results:
                return results[0].alpha_2
        except LookupError:
            pass
    logger.warning(
        f"Could not resolve country '{name}' to ISO code, defaulting to 'DE'"
    )
    return "DE"


def _rate_to_percent(vat_rate: Decimal) -> Decimal:
    """Convert a VAT rate fraction (0–1) to a plain xs:decimal-safe percentage.

    Decimal arithmetic can produce scientific notation (e.g. 0E-10) for zero,
    which xs:decimal rejects. Always return Decimal("0") for zero rates.
    """
    pct = vat_rate * 100
    return Decimal("0") if pct == 0 else pct


#: BT-121 exemption reason code and BT-120 text required by EN16931 BR-O-10.
VATEX_OUTSIDE_SCOPE = "VATEX-EU-O"
VATEX_OUTSIDE_SCOPE_REASON = "Not subject to VAT"


def _tax_currency(user: User) -> str:
    """The currency VAT is accounted in — the operating country's tax currency."""
    try:
        return get_tax_system(user.operating_country or "Germany").currency
    except NotImplementedError:
        return "EUR"


def _vat_in_tax_currency(
    invoice: Invoice, total_tax: Decimal, currency: str, tax_currency: str
) -> Decimal:
    """BT-111 — the invoice's VAT total expressed in the accounting currency.

    For the cases Tuttle supports (reverse charge, outside scope) a foreign-
    currency invoice carries no VAT, so this is zero and needs no rate at all.
    """
    if not total_tax:
        return Decimal("0.00")
    converted = convert(total_tax, currency, tax_currency, invoice.date)
    if converted is None:
        raise ValueError(
            f"Invoice {invoice.number or invoice.id} carries VAT in {currency} but "
            f"the {currency}/{tax_currency} rate for {invoice.date:%Y-%m} could not "
            "be resolved, so BT-111 cannot be computed."
        )
    return converted


# -- Schema name mapping ------------------------------------------------------

ZUGFERD_SCHEMAS = {
    "EN16931": "FACTUR-X_EN16931",
    "EXTENDED": "FACTUR-X_EXTENDED",
    "BASIC": "FACTUR-X_BASIC",
    "MINIMUM": "FACTUR-X_MINIMUM",
    "XRECHNUNG": "urn:cen.eu:en16931:2017#compliant#urn:xeink:spec:XRechnung:3.0",
}

GUIDELINE_IDS = {
    "EN16931": "urn:cen.eu:en16931:2017",
    "EXTENDED": "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended",
    "BASIC": "urn:cen.eu:en16931:2017#compliant#urn:factur-x.eu:1p0:basic",
    "MINIMUM": "urn:factur-x.eu:1p0:minimum",
    "XRECHNUNG": "urn:cen.eu:en16931:2017#compliant#urn:xeink:spec:XRechnung:3.0",
}


# -- Core builder -------------------------------------------------------------


def build_zugferd_document(
    invoice: Invoice,
    user: User,
    profile: str = "EN16931",
) -> Document:
    """Build a drafthorse Document from a Tuttle Invoice.

    Args:
        invoice: A Tuttle Invoice with loaded relationships (contract, items, project).
        user: The freelancer / seller.
        profile: ZUGFeRD profile level (EN16931, EXTENDED, BASIC, MINIMUM, XRECHNUNG).

    Returns:
        A drafthorse Document ready for serialization.
    """
    contract = invoice.contract
    client = contract.client

    doc = Document()
    guideline_id = GUIDELINE_IDS.get(profile, GUIDELINE_IDS["EN16931"])
    doc.context.guideline_parameter.id = guideline_id

    # -- Header ---------------------------------------------------------------
    doc.header.id = invoice.number or str(invoice.id)
    doc.header.type_code = "380"  # commercial invoice
    doc.header.issue_date_time = invoice.date

    is_minimum = profile == "MINIMUM"
    # BR-O-11/12: category O never coexists with another category on one invoice.
    outside_scope = invoice.is_outside_scope

    # -- Seller (User) --------------------------------------------------------
    doc.trade.agreement.seller.name = user.name
    if user.address:
        if not is_minimum:
            doc.trade.agreement.seller.address.line_one = (
                f"{user.address.street} {user.address.number}".strip()
            )
            doc.trade.agreement.seller.address.city_name = user.address.city
            doc.trade.agreement.seller.address.postcode = user.address.postal_code
        doc.trade.agreement.seller.address.country_id = country_to_iso(
            user.address.country
        )
    # BR-O-02 forbids the seller VAT identifier on invoices outside the scope of
    # tax. §14 UStG still wants an identifier, so fall back to the tax number,
    # which CII carries under a different scheme ("FC", Steuernummer).
    if outside_scope:
        if user.tax_number:
            doc.trade.agreement.seller.tax_registrations.add(
                TaxRegistration(id=("FC", user.tax_number))
            )
        else:
            logger.warning(
                "Invoice is outside the scope of VAT but the user has no tax "
                "number; the e-invoice will carry no seller tax identifier."
            )
    elif user.VAT_number:
        doc.trade.agreement.seller.tax_registrations.add(
            TaxRegistration(id=("VA", user.VAT_number))
        )
    elif user.tax_number:
        # No USt-IdNr yet: §14 UStG still needs an identifier, and FC (Steuernummer)
        # is legal on any invoice — unlike VA (BR-O-02).
        doc.trade.agreement.seller.tax_registrations.add(
            TaxRegistration(id=("FC", user.tax_number))
        )
    if user.email and not is_minimum:
        doc.trade.agreement.seller.electronic_address.uri_ID = ("EM", user.email)

    # -- Buyer (Client) -------------------------------------------------------
    doc.trade.agreement.buyer.name = client.invoice_recipient_name
    buyer_address = client.address
    if buyer_address:
        if not is_minimum:
            doc.trade.agreement.buyer.address.line_one = (
                f"{buyer_address.street} {buyer_address.number}".strip()
            )
            doc.trade.agreement.buyer.address.city_name = buyer_address.city
            doc.trade.agreement.buyer.address.postcode = buyer_address.postal_code
        doc.trade.agreement.buyer.address.country_id = country_to_iso(
            buyer_address.country
        )
    buyer_vat = getattr(client, "vat_number", None)
    if buyer_vat and not outside_scope:  # BR-O-02
        doc.trade.agreement.buyer.tax_registrations.add(
            TaxRegistration(id=("VA", buyer_vat))
        )

    # -- Currency -------------------------------------------------------------
    currency = contract.currency or "EUR"
    doc.trade.settlement.currency_code = currency

    # -- Payment means (not in MINIMUM) ----------------------------------------
    if not is_minimum and user.bank_account and user.bank_account.IBAN:
        pm = PaymentMeans()
        pm.type_code = "58"  # SEPA credit transfer
        pm.payee_account.iban = user.bank_account.IBAN
        if user.bank_account.BIC and profile not in ("BASIC",):
            pm.payee_institution.bic = user.bank_account.BIC
        doc.trade.settlement.payment_means.add(pm)

    # -- Line items & tax (not in MINIMUM) -------------------------------------
    total_tax = Decimal("0")

    if not is_minimum:
        # Keyed by (category, rate) rather than rate alone: a zero-rated line and
        # an outside-scope line both sit at 0% but must not collapse into one
        # breakdown.
        tax_aggregates: dict[tuple[str, Decimal], Decimal] = {}
        for idx, item in enumerate(invoice.items, start=1):
            li = LineItem()
            li.document.line_id = str(idx)
            li.product.name = item.description or f"Item {idx}"

            unit_code = unit_to_unece(item.unit)
            quantity = Decimal(str(item.quantity))
            net_price = item.unit_price
            line_total = Decimal(str(item.subtotal))
            category = normalize_tax_category(item.VAT_category).value
            vat_pct = _rate_to_percent(item.VAT_rate)

            li.agreement.net.amount = net_price
            li.agreement.net.basis_quantity = (Decimal("1"), unit_code)
            li.delivery.billed_quantity = (quantity, unit_code)
            li.settlement.trade_tax.type_code = "VAT"
            li.settlement.trade_tax.category_code = category
            # BR-O-05: an outside-scope line carries no rate at all.
            if category != TaxCategory.outside_scope.value:
                li.settlement.trade_tax.rate_applicable_percent = vat_pct
            li.settlement.monetary_summation.total_amount = line_total
            doc.trade.items.add(li)
            key = (category, vat_pct)
            tax_aggregates[key] = tax_aggregates.get(key, Decimal("0")) + line_total

        # -- Tax summary ------------------------------------------------------
        for (category, rate_pct), basis in tax_aggregates.items():
            tax_amount = (basis * rate_pct / Decimal("100")).quantize(Decimal("0.01"))
            total_tax += tax_amount
            trade_tax = ApplicableTradeTax()
            trade_tax.calculated_amount = tax_amount
            trade_tax.basis_amount = basis
            trade_tax.type_code = "VAT"
            trade_tax.category_code = category
            if category == TaxCategory.outside_scope.value:
                # BR-O-10 requires a reason; BR-48 exempts O from carrying a rate.
                trade_tax.exemption_reason_code = VATEX_OUTSIDE_SCOPE
                trade_tax.exemption_reason = VATEX_OUTSIDE_SCOPE_REASON
            else:
                trade_tax.rate_applicable_percent = rate_pct
            doc.trade.settlement.trade_tax.add(trade_tax)
    else:
        # MINIMUM carries no breakdown, only the total, so the category does not
        # matter here and the basis can be aggregated by rate alone.
        rate_bases: dict[Decimal, Decimal] = {}
        for item in invoice.items:
            pct = _rate_to_percent(item.VAT_rate)
            rate_bases[pct] = rate_bases.get(pct, Decimal("0")) + Decimal(
                str(item.subtotal)
            )
        for rate_pct, basis in rate_bases.items():
            total_tax += (basis * rate_pct / Decimal("100")).quantize(Decimal("0.01"))

    # -- Monetary summation ---------------------------------------------------
    line_total_sum = invoice.sum
    grand_total = line_total_sum + total_tax
    due_amount = grand_total

    if not is_minimum:
        doc.trade.settlement.monetary_summation.line_total = line_total_sum
        doc.trade.settlement.monetary_summation.charge_total = Decimal("0.00")
        doc.trade.settlement.monetary_summation.allowance_total = Decimal("0.00")
    doc.trade.settlement.monetary_summation.tax_basis_total = line_total_sum
    doc.trade.settlement.monetary_summation.tax_total = (total_tax, currency)

    # BT-6 / BT-111: when the invoice currency differs from the VAT accounting
    # currency, EN16931 requires the tax currency code and the VAT total in it.
    tax_currency = _tax_currency(user)
    if not is_minimum and tax_currency != currency:
        doc.trade.settlement.tax_currency_code = tax_currency
        doc.trade.settlement.monetary_summation.tax_total_other_currency.add(
            (
                _vat_in_tax_currency(invoice, total_tax, currency, tax_currency),
                tax_currency,
            )
        )

    doc.trade.settlement.monetary_summation.grand_total = grand_total
    doc.trade.settlement.monetary_summation.due_amount = due_amount

    # -- Payment terms (not in MINIMUM) ----------------------------------------
    if not is_minimum and contract.term_of_payment:
        terms = PaymentTerms()
        due_date = invoice.date + timedelta(days=contract.term_of_payment)
        terms.due = datetime(
            due_date.year, due_date.month, due_date.day, tzinfo=timezone.utc
        )
        terms.description = f"Net {contract.term_of_payment} days"
        doc.trade.settlement.terms.add(terms)

    return doc


def serialize_zugferd_xml(
    invoice: Invoice,
    user: User,
    profile: str = "EN16931",
    validate: bool = True,
) -> bytes:
    """Generate ZUGFeRD/Factur-X XML from a Tuttle Invoice.

    Args:
        invoice: A Tuttle Invoice with loaded relationships.
        user: The freelancer / seller.
        profile: ZUGFeRD profile level.
        validate: Whether to validate against XSD (raises on failure).

    Returns:
        The serialized XML as bytes.
    """
    doc = build_zugferd_document(invoice, user, profile=profile)
    schema = ZUGFERD_SCHEMAS.get(profile) if validate else None
    return doc.serialize(schema=schema)


def embed_zugferd_in_pdf(
    pdf_path: str,
    invoice: Invoice,
    user: User,
    profile: str = "EN16931",
) -> None:
    """Embed ZUGFeRD XML into an existing PDF file (in-place).

    Args:
        pdf_path: Path to the PDF file to augment.
        invoice: A Tuttle Invoice with loaded relationships.
        user: The freelancer / seller.
        profile: ZUGFeRD profile level.
    """
    xml = serialize_zugferd_xml(invoice, user, profile=profile)
    with open(pdf_path, "rb") as f:
        original_pdf = f.read()
    result_pdf = attach_xml(original_pdf, xml)
    with open(pdf_path, "wb") as f:
        f.write(result_pdf)
    logger.info(f"Embedded ZUGFeRD ({profile}) XML into {pdf_path}")
