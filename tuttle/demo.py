import datetime
import random
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, Iterator, List, NamedTuple, Optional
from zoneinfo import ZoneInfo

import faker
import ics
import numpy
from loguru import logger
from pandas import DataFrame
from sqlmodel import Session, create_engine, select

from tuttle import invoicing, rendering, timetracking
from tuttle.calendar import ICSCalendar
from tuttle.data_dir import get_data_dir
from tuttle.db_schema import ensure_schema
from tuttle.model import (
    Address,
    BankAccount,
    ChargeBasis,
    Client,
    ClientContact,
    Contact,
    Contract,
    ContractCharge,
    ContractType,
    Cycle,
    FinancialGoal,
    Invoice,
    InvoiceItem,
    InvoiceNote,
    PaymentMilestone,
    Project,
    RecurringExpense,
    TaskRule,
    TaskRuleNotice,
    TaxCategory,
    Timesheet,
    TimeTrackingItem,
    TimeUnit,
    User,
)

# ---------------------------------------------------------------------------
# Random heating-repair records, for tests
# ---------------------------------------------------------------------------

_HEATING_TASKS = [
    "Thermostat calibration",
    "Radiator bleeding",
    "Boiler diagnostics",
    "Pump pressure test",
    "Flue gas analysis",
    "Pipe insulation check",
    "Expansion vessel service",
    "Control panel firmware update",
    "Heat exchanger cleaning",
    "Safety valve inspection",
]

_HEATING_INVOICE_ITEMS = [
    ("Labor: boiler service", "hours"),
    ("Replacement valve DN20", "hours"),
    ("Thermostat head Danfoss RA-N", "hours"),
    ("Circulation pump Grundfos UPS", "hours"),
    ("Pipe insulation material", "hours"),
    ("Flue gas measurement", "hours"),
    ("Emergency callout surcharge", "hours"),
    ("Travel to site", "hours"),
]


def create_fake_user(
    fake: faker.Faker,
) -> User:
    """Create a fake user."""
    user = User(
        name=fake.name(),
        email=fake.email(),
        subtitle=fake.job(),
        VAT_number=fake.ean8(),
    )
    return user


def create_fake_contact(
    fake: faker.Faker,
) -> Contact:
    split_address_lines = fake.address().splitlines()
    street_line = split_address_lines[0]
    city_line = split_address_lines[1]
    try:
        street = street_line.split(" ", 1)[0]
        number = street_line.split(" ", 1)[1]
        city = city_line.split(" ")[1]
        postal_code = city_line.split(" ")[0]
    except IndexError:
        street = street_line
        number = ""
        city = city_line
        postal_code = ""
    a = Address(
        street=street,
        number=number,
        city=city,
        postal_code=postal_code,
        country=fake.country(),
    )
    first_name, last_name = fake.name().split(" ", 1)
    contact = Contact(
        first_name=first_name,
        last_name=last_name,
        email=fake.email(),
        company=fake.company(),
        address_id=a.id,
        address=a,
    )
    return contact


def create_fake_address(fake: faker.Faker) -> Address:
    """Create a fake postal address."""
    street_line = fake.street_address()
    city_line = fake.city()
    try:
        street = street_line.rsplit(" ", 1)[0]
        number = street_line.rsplit(" ", 1)[1]
    except IndexError:
        street = street_line
        number = ""
    return Address(
        street=street,
        number=number,
        city=city_line,
        postal_code=fake.postcode(),
        country=fake.country(),
    )


def create_fake_client(
    fake: faker.Faker,
    invoicing_contact: Optional[Contact] = None,
    with_contact: bool = True,
) -> Client:
    vat_number = f"DE{fake.unique.random_number(digits=9, fix_len=True)}"
    if with_contact:
        if invoicing_contact is None:
            invoicing_contact = create_fake_contact(fake)
        return Client(
            name=fake.company(),
            vat_number=vat_number,
            invoicing_contact=invoicing_contact,
        )
    return Client(
        name=fake.company(),
        vat_number=vat_number,
        address=create_fake_address(fake),
    )


def create_fake_contract(
    fake: faker.Faker,
    client: Optional[Client] = None,
) -> Contract:
    """Create a fake contract for the given client."""
    if client is None:
        client = create_fake_client(fake)
    unit = random.choice(list(TimeUnit))
    if unit == TimeUnit.day:
        rate = fake.random_int(200, 1000)
    elif unit == TimeUnit.hour:
        rate = fake.random_int(10, 100)
    else:
        rate = fake.random_int(1, 1000)
    return Contract(
        title=f"{client.name} service contract",
        client=client,
        signature_date=fake.date_this_year(before_today=True),
        start_date=fake.date_this_year(after_today=True),
        rate=rate,
        currency="EUR",
        VAT_rate=Decimal(round(random.uniform(0.05, 0.2), 2)),
        unit=unit,
        units_per_workday=random.randint(1, 12),
        volume=fake.random_int(1, 1000),
        term_of_payment=fake.random_int(1, 31),
        billing_cycle=random.choice([Cycle.weekly, Cycle.monthly, Cycle.quarterly]),
    )


def create_fake_project(
    fake: faker.Faker,
    contract: Optional[Contract] = None,
) -> Project:
    if contract is None:
        contract = create_fake_contract(fake)

    project_title = fake.bs().replace("/", "-")
    project_tag = f"#{'-'.join(project_title.split(' ')[:2]).lower()}"

    project = Project(
        title=project_title,
        tag=project_tag,
        description=fake.paragraph(nb_sentences=2),
        is_completed=fake.pybool(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=80),
        contract=contract,
    )
    return project


def invoice_number_counting():
    count = 0
    while True:
        count += 1
        yield count


invoice_number_counter = invoice_number_counting()


def create_fake_timesheet(
    fake: faker.Faker,
    project: Optional[Project] = None,
) -> Timesheet:
    """
    Create a fake timesheet object with random values.

    Args:
    project (Project): The project associated with the timesheet.
    fake (faker.Faker): An instance of the Faker class to generate random values.

    Returns:
    Timesheet: A fake timesheet object.
    """
    if project is None:
        project = create_fake_project(fake)
    timesheet = Timesheet(
        title=f"Timesheet – {project.title}",
        comment=f"Work log for {project.title}",
        date=datetime.date.today(),
        period_start=datetime.date.today() - datetime.timedelta(days=30),
        period_end=datetime.date.today(),
        project=project,
    )
    number_of_items = fake.random_int(min=2, max=5)
    for _ in range(number_of_items):
        task = random.choice(_HEATING_TASKS)
        hours = fake.random_int(min=1, max=8)
        begin = fake.date_time_this_year(before_now=True, after_now=False)
        time_tracking_item = TimeTrackingItem(
            timesheet=timesheet,
            begin=begin,
            end=begin + datetime.timedelta(hours=hours),
            duration=datetime.timedelta(hours=hours),
            title=f"{task} {project.tag}",
            tag=project.tag,
            description=task,
        )
        timesheet.items.append(time_tracking_item)
    return timesheet


def create_fake_invoice(
    fake: faker.Faker,
    project: Optional[Project] = None,
    user: Optional[User] = None,
    render: bool = True,
    invoice_date: Optional[date] = None,
    paid: Optional[bool] = None,
    sent: Optional[bool] = None,
    cancelled: bool = False,
) -> Invoice:
    """
    Create a fake invoice object with random values.

    Args:
    project (Project): The project associated with the invoice.
    fake (faker.Faker): An instance of the Faker class to generate random values.
    invoice_date: The date for the invoice. Defaults to today.
    paid: Whether the invoice is paid. Random if None.
    sent: Whether the invoice was sent. Random if None.
    cancelled: Whether the invoice is cancelled.

    Returns:
    Invoice: A fake invoice object.
    """
    if project is None:
        project = create_fake_project(fake)

    if user is None:
        user = create_fake_user(fake)

    inv_date = invoice_date or datetime.date.today()
    invoice_number = f"{inv_date.strftime('%Y-%m-%d')}-{next(invoice_number_counter)}"
    invoice = Invoice(
        number=invoice_number,
        date=inv_date,
        sent=sent if sent is not None else fake.pybool(),
        paid=paid if paid is not None else fake.pybool(),
        cancelled=cancelled,
        contract=project.contract,
        project=project,
        rendered=render,
    )
    contract = project.contract
    item_end = inv_date - timedelta(days=random.randint(1, 10))
    item_start = item_end - timedelta(days=random.randint(5, 25))

    if contract.charges:
        # A contract with additional charges bills one work line at the
        # contractual rate plus a line per charge, the same shape
        # invoicing.generate_invoice produces from tracked time.
        days_worked = Decimal(fake.random_int(min=2, max=5))
        InvoiceItem(
            start_date=item_start,
            end_date=item_end,
            quantity=float(days_worked),
            unit=contract.unit.value,
            unit_price=Decimal(str(contract.rate)),
            description=project.title,
            VAT_rate=contract.VAT_rate,
            VAT_category=contract.VAT_category,
            invoice=invoice,
        )
        # Recurring charges only. A one-time charge belongs on a single
        # invoice, which is settled once the whole history exists — see
        # apply_one_time_charges.
        for charge_item in invoicing.build_charge_items(
            invoicing._applicable_charges(contract, None),
            contract=contract,
            billable_quantity=days_worked,
            start_date=item_start,
            end_date=item_end,
        ):
            charge_item.invoice = invoice
    else:
        number_of_items = fake.random_int(min=1, max=4)
        used_items = random.sample(
            _HEATING_INVOICE_ITEMS,
            k=min(number_of_items, len(_HEATING_INVOICE_ITEMS)),
        )
        for desc, unit in used_items:
            unit_price = abs(round(numpy.random.normal(75, 20), 2))
            item_end = inv_date - timedelta(days=random.randint(1, 10))
            item_start = item_end - timedelta(days=random.randint(5, 25))
            InvoiceItem(
                start_date=item_start,
                end_date=item_end,
                quantity=fake.random_int(min=1, max=8),
                unit=unit,
                unit_price=Decimal(unit_price),
                description=desc,
                # Follow the contract: a USD contract to a US client is outside the
                # scope of German VAT, so its items must not carry 19%.
                VAT_rate=contract.VAT_rate,
                VAT_category=contract.VAT_category,
                invoice=invoice,
            )

    # an invoice is created together with a timesheet. For the sake of simplicity, timesheet and invoice items are not linked.
    timesheet = create_fake_timesheet(fake, project)
    # attach timesheet to invoice
    timesheet.invoice = invoice
    assert len(invoice.timesheets) == 1

    if render:
        # render invoice
        try:
            rendering.render_invoice(
                user=user,
                invoice=invoice,
                out_dir=get_data_dir() / "Invoices",
                only_final=True,
            )
            logger.info(f"✅ rendered invoice for {project.title}")
        except Exception as ex:
            logger.error(f"❌ Error rendering invoice for {project.title}: {ex}")
            logger.exception(ex)
        # render timesheet
        try:
            rendering.render_timesheet(
                user=user,
                timesheet=timesheet,
                out_dir=get_data_dir() / "Timesheets",
                only_final=True,
            )
            logger.info(f"✅ rendered timesheet for {project.title}")
        except Exception as ex:
            logger.error(f"❌ Error rendering timesheet for {project.title}: {ex}")
            logger.exception(ex)

    return invoice


# ---------------------------------------------------------------------------
# Harry Tuttle, the demo user
# ---------------------------------------------------------------------------
# A fixed cast, small enough to walk through in a demo, where each record is
# there to show a feature; the comments say which. Dates are relative to the
# day of installation, so the demo always looks current.

# Seeds the demo calendar: installing twice on one day gives the same hours.
_DEMO_SEED = 276

_CET = ZoneInfo("CET")

_DEMO_INVOICE_NOTES = (
    "Thank you for your business. Please include the invoice number with your payment.",
    "No form 27B/6 required: just quote the invoice number when you pay.",
)


def _month_start(day: date, months_back: int = 0) -> date:
    """First day of the month *months_back* months before the month of *day*, or after it if negative."""
    index = day.year * 12 + day.month - 1 - months_back
    return date(index // 12, index % 12 + 1, 1)


def _add_workdays(day: date, n: int) -> date:
    """The weekday *n* weekdays after *day*, or before it if *n* is negative."""
    step = 1 if n > 0 else -1
    while n:
        day += timedelta(days=step)
        if day.weekday() < 5:
            n -= step
    return day


def _load_demo_signature() -> Optional[str]:
    """Load the demo signature image and process it into a data URI."""
    import base64

    from .app.users.intent import _normalize_signature

    sig_path = Path(__file__).parent / "demo_assets" / "harry_tuttle_signature.png"
    if not sig_path.exists():
        logger.warning(f"Demo signature not found: {sig_path}")
        return None
    raw = sig_path.read_bytes()
    data_uri = "data:image/png;base64," + base64.b64encode(raw).decode()
    try:
        return _normalize_signature(data_uri)
    except Exception as ex:
        logger.warning(f"Could not process demo signature: {ex}")
        return None


def create_demo_user() -> User:
    user = User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        website="https://tuttle-dev.github.io/tuttle/",
        email="mail@tuttle.com",
        phone_number="+55555555555",
        # Taxed in Germany: the tax model behind Tax & Reserves and Salary,
        # and the 19% VAT on his contracts.
        operating_country="Germany",
        VAT_number="27B-6",
        tax_number="27B/6-1985",
        signature=_load_demo_signature(),
        address=Address(
            street="Main Street",
            number="450",
            city="Somewhere",
            postal_code="555555",
            country="Brazil",
        ),
        bank_accounts=[
            BankAccount(
                name="Harry Tuttle",
                IBAN="BZ99830994950003161565",
                BIC="BANKINFO101",
                is_default=True,
            ),
            BankAccount(
                name="Harry Tuttle",
                IBAN="US88589600002547441617",
                BIC="TRWIBEB1",
                is_default=False,
            ),
        ],
    )
    return user


def create_demo_business(user: User, today: date) -> tuple[Dict[str, Project], List[ClientContact]]:
    """Harry's clients, contacts, contracts and projects, the projects keyed by tag.

    Each stage of the project board has a project, and each kind of contract
    an example: hourly with a budget of hours, a retainer, a day rate with
    extra charges, fixed prices with payment schedules, and one in US dollars.
    """

    def somewhere(street: str, number: str) -> Address:
        return Address(street=street, number=number, postal_code="55555", city="Somewhere", country="Brazil")

    def contract(**terms) -> Contract:
        defaults = dict(
            currency="EUR",
            VAT_rate=Decimal("0.19"),
            unit=TimeUnit.hour,
            units_per_workday=8,
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
        )
        return Contract(**(defaults | terms))

    # -- clients and their contacts ---------------------------------------------

    sam_lowry_contact = Contact(
        first_name="Sam",
        last_name="Lowry",
        email="lowry@centralservices.com",
        address=somewhere("Main Street", "9999"),
    )
    jill_layton = Contact(
        first_name="Jill",
        last_name="Layton",
        email="layton@centralservices.com",
        company="Central Services",
        address=somewhere("Main Street", "42"),
    )
    # Archibald Buttle — wrongly arrested instead of Tuttle
    archibald_buttle = Contact(
        first_name="Archibald",
        last_name="Buttle",
        email="buttle@centralservices.com",
        address=somewhere("Shangri-La Towers", "412"),
    )
    veronica_buttle = Contact(
        first_name="Veronica",
        last_name="Buttle",
        email="buttle@shangrilatowers.com",
        company="Shangri-La Towers",
        address=somewhere("Shangri-La Towers", "412"),
    )
    # Sam's friend at Information Retrieval
    jack_lint = Contact(
        first_name="Jack",
        last_name="Lint",
        email="lint@ministryofinformation.gov",
        company="Ministry of Information",
        address=somewhere("Ministry of Information", "1"),
    )
    harvey_lime = Contact(
        first_name="Harvey",
        last_name="Lime",
        email="lime@ductworksecurity.com",
        company="Ductwork Security Inc.",
        address=Address(
            street="Market Street",
            number="1200",
            postal_code="94103",
            city="San Francisco",
            country="United States",
        ),
    )

    # Invoices go to the accountant, the invoicing contact chosen for Central Services.
    central_services = Client(
        name="Central Services",
        vat_number="BR12345678901",
        address=somewhere("Main Street", "42"),
        invoicing_contact=jill_layton,
    )
    sam_lowry = Client(name="Sam Lowry", invoicing_contact=sam_lowry_contact)
    # The tower block where the Buttles live, and where nothing works.
    shangri_la = Client(
        name="Shangri-La Towers",
        vat_number="BR23456789012",
        address=somewhere("Shangri-La Towers", "1"),
        invoicing_contact=veronica_buttle,
    )
    ministry = Client(name="Ministry of Information", vat_number="BR34567890123", invoicing_contact=jack_lint)
    ductwork_security = Client(name="Ductwork Security Inc.", invoicing_contact=harvey_lime)

    # A contact can work for several clients, in a role at each.
    client_contacts = [
        ClientContact(client=central_services, contact=sam_lowry_contact, role="project lead"),
        ClientContact(client=central_services, contact=jill_layton, role="accountant"),
        ClientContact(client=central_services, contact=archibald_buttle, role="shoe repair"),
        ClientContact(client=sam_lowry, contact=sam_lowry_contact, role="invoicing"),
        ClientContact(client=shangri_la, contact=veronica_buttle, role="tenants' representative"),
        ClientContact(client=ministry, contact=jack_lint, role="Information Retrieval"),
        ClientContact(client=ductwork_security, contact=harvey_lime, role="invoicing"),
    ]

    projects: List[Project] = []

    # -- Central Services ----------------------------------------------------------

    # Hourly maintenance with a budget of hours, billed by the quarter: five
    # complete quarters so far.
    maintenance_start = _month_start(today, 15 + (today.month - 1) % 3)
    projects.append(
        Project(
            title="Heating Engineering",
            tag="#heatingengineering",
            description="Central heating system maintenance and engineering",
            start_date=maintenance_start,
            end_date=today + timedelta(days=180),
            contract=contract(
                title="Annual heating maintenance – Central Services",
                client=central_services,
                signature_date=maintenance_start - timedelta(days=14),
                start_date=maintenance_start,
                rate=Decimal("85"),
                volume=600,
                billing_cycle=Cycle.quarterly,
            ),
        )
    )

    # A fixed price paid in three instalments: the first invoiced as a
    # deposit, two still open.
    modernisation_start = today - timedelta(days=100)
    modernisation = contract(
        title="Heating System Modernisation – Central Services",
        client=central_services,
        signature_date=modernisation_start - timedelta(days=20),
        start_date=modernisation_start,
        type=ContractType.fixed_price,
        fixed_price=Decimal("24000"),
        volume=320,
    )
    for position, (title, percentage) in enumerate(
        (("On signing", 40), ("Plant room commissioned", 40), ("Handover and balancing report", 20))
    ):
        PaymentMilestone(contract=modernisation, title=title, percentage=Decimal(percentage), position=position)
    projects.append(
        Project(
            title="Heating Modernisation",
            tag="#modernisation",
            description="Replace the plant room and rebalance the risers, billed in three instalments",
            start_date=modernisation_start,
            end_date=today + timedelta(days=120),
            contract=modernisation,
        )
    )

    # Finished and paid. Its invoice was written outside Tuttle and has no
    # timesheet, so only the completed mark keeps its calendar time out of
    # Planned revenue.
    inspection_start = today - timedelta(days=85)
    inspection_end = today - timedelta(days=30)
    projects.append(
        Project(
            title="Duct Inspection",
            tag="#ductinspection",
            description="Inspection of the ductwork in the Ministry annex, billed in a single invoice",
            is_completed=True,
            stage="Completed",
            start_date=inspection_start,
            end_date=inspection_end,
            contract=contract(
                title="Duct Inspection – Central Services",
                client=central_services,
                signature_date=inspection_start - timedelta(days=10),
                start_date=inspection_start,
                end_date=inspection_end,
                rate=Decimal("80"),
                volume=20,
                is_completed=True,
            ),
        )
    )

    # -- Sam Lowry -------------------------------------------------------------------

    # A fixed price in two halves, deposit and final invoice. The repair is
    # done and the final invoice overdue; the project stays Active until Harry
    # marks it completed.
    repair_start = today - timedelta(days=80)
    repair = contract(
        title="Heating Repair – Sam Lowry",
        client=sam_lowry,
        signature_date=repair_start - timedelta(days=7),
        start_date=repair_start,
        type=ContractType.fixed_price,
        fixed_price=Decimal("5000"),
        volume=20,
    )
    for position, title in enumerate(("Half upfront on commissioning", "Half on delivery")):
        PaymentMilestone(contract=repair, title=title, percentage=Decimal("50"), position=position)
    projects.append(
        Project(
            title="Heating Repair",
            tag="#heatingrepair",
            description="Fix the heating in Sam's flat, which Central Services never got round to",
            start_date=repair_start,
            end_date=today - timedelta(days=24),
            contract=repair,
        )
    )

    # -- Shangri-La Towers ---------------------------------------------------

    # A retainer has no agreed total, only the hours Harry expects to put in
    # each week: its future revenue follows that pace.
    retainer_start = _month_start(today, 9)
    projects.append(
        Project(
            title="Emergency Repairs",
            tag="#emergency",
            description="On-call repairs in a tower block where nothing works",
            start_date=retainer_start,
            end_date=today + timedelta(days=180),
            contract=contract(
                title="Emergency repair retainer – Shangri-La Towers",
                client=shangri_la,
                signature_date=retainer_start - timedelta(days=10),
                start_date=retainer_start,
                rate=Decimal("95"),
                expected_units_per_week=6,
            ),
        )
    )

    # Billed by the day, two days a week until the 60 agreed days are used up,
    # with a daily allowance and a one-off survey fee: charges that do not
    # come from tracked time.
    retrofit_start = _month_start(today, 4)
    projects.append(
        Project(
            title="Boiler Retrofit",
            tag="#boilerretrofit",
            description="On-site boiler retrofit billed by the day, with a daily allowance",
            start_date=retrofit_start,
            end_date=today + timedelta(days=180),
            contract=contract(
                title="On-Site Boiler Retrofit – Shangri-La Towers",
                client=shangri_la,
                signature_date=retrofit_start - timedelta(days=14),
                start_date=retrofit_start,
                rate=Decimal("640"),
                unit=TimeUnit.day,
                volume=60,
                expected_units_per_week=2,
                charges=[
                    ContractCharge(
                        description="Daily allowance (travel and consumables)",
                        amount=Decimal("85"),
                        basis=ChargeBasis.per_unit,
                        position=0,
                    ),
                    ContractCharge(
                        description="Site survey and setup fee",
                        amount=Decimal("450"),
                        basis=ChargeBasis.once,
                        position=1,
                    ),
                ],
            ),
        )
    )

    # -- Ductwork Security -----------------------------------------------------------

    # Harry is taxed in Germany but bills this US client in dollars, into his
    # dollar account: the mixed-currency case. B2B to a non-EU recipient, so
    # the supply is outside the scope of German VAT (§ 3a Abs. 2 UStG).
    review_start = _month_start(today, 2)
    projects.append(
        Project(
            title="Duct Control Review",
            tag="#ductcontrol",
            description="Review of the pneumatic duct control systems",
            start_date=review_start,
            end_date=today + timedelta(days=60),
            contract=contract(
                title="Duct Control Review – Ductwork Security Inc.",
                client=ductwork_security,
                signature_date=review_start - timedelta(days=10),
                start_date=review_start,
                rate=Decimal("1000"),
                currency="USD",
                VAT_rate=Decimal("0"),
                VAT_category=TaxCategory.outside_scope,
                unit=TimeUnit.day,
                volume=6,
                bank_account=next(a for a in user.bank_accounts if not a.is_default),
            ),
        )
    )

    # -- Ministry of Information: the pipeline --------------------------------------------

    # Signed and starting in three weeks. None of it is in the calendar yet,
    # so all of it is Contracted revenue.
    heat_pump_start = today + timedelta(days=21)
    heat_pump_end = heat_pump_start + timedelta(days=120)
    projects.append(
        Project(
            title="Heat Pump Conversion",
            tag="#heatpump",
            description="Replace the gas boiler in the Department of Records with an air-source heat pump",
            start_date=heat_pump_start,
            end_date=heat_pump_end,
            contract=contract(
                title="Heat Pump Conversion – Ministry of Information",
                client=ministry,
                signature_date=today - timedelta(days=5),
                start_date=heat_pump_start,
                end_date=heat_pump_end,
                rate=Decimal("85"),
                volume=160,
            ),
        )
    )

    # Quoted and not accepted yet: counts for nothing until it is.
    underfloor_start = today + timedelta(days=45)
    underfloor_end = underfloor_start + timedelta(days=60)
    projects.append(
        Project(
            title="Underfloor Heating",
            tag="#underfloor",
            description="Underfloor heating for Mr. Helpmann's office, quoted at a fixed price",
            stage="Offer",
            start_date=underfloor_start,
            end_date=underfloor_end,
            contract=contract(
                title="Underfloor Heating – Ministry of Information",
                client=ministry,
                start_date=underfloor_start,
                end_date=underfloor_end,
                type=ContractType.fixed_price,
                fixed_price=Decimal("9800"),
            ),
        )
    )

    # An enquiry, nothing quoted yet.
    radiator_start = today + timedelta(days=90)
    projects.append(
        Project(
            title="Radiator Upgrade",
            tag="#radiators",
            description="Panel radiators for the Information Retrieval wing",
            stage="Lead",
            start_date=radiator_start,
            contract=contract(
                title="Radiator Upgrade – Ministry of Information",
                client=ministry,
                start_date=radiator_start,
                rate=Decimal("85"),
            ),
        )
    )

    return {project.tag: project for project in projects}, client_contacts


class _Routine(NamedTuple):
    """How Harry's weeks go on one project."""

    weekdays: tuple  # Monday is 0
    start_hour: int
    hours: tuple  # an entry's length is drawn from these; none for a whole day on site
    chance: float  # of an entry on one of the weekdays
    tasks: tuple
    planned_ahead: bool = True  # emergencies can't be


# Arranged so that no two entries on one day overlap.
_DEMO_ROUTINES = {
    "#heatingengineering": _Routine(
        (1, 3),
        8,
        (3, 3, 4),
        0.9,
        ("Boiler diagnostics", "Flue gas analysis", "Pump pressure test", "Safety valve inspection"),
    ),
    "#modernisation": _Routine((4,), 8, (4, 5), 0.9, ("Plant room installation", "Riser balancing", "Pipework")),
    "#ductinspection": _Routine((4,), 14, (2, 3), 0.9, ("Duct inspection",)),
    "#heatingrepair": _Routine((1,), 13, (2, 3), 0.9, ("Repair at Sam's flat",)),
    "#emergency": _Routine(
        (0, 1, 2, 3, 4),
        17,
        (1, 2, 2, 3),
        0.6,
        ("Callout: burst pipe", "Callout: no hot water", "Callout: radiator leak", "Callout: boiler lockout"),
        planned_ahead=False,
    ),
    "#boilerretrofit": _Routine((0, 2), 8, (), 0.95, ("On site",)),
    "#ductcontrol": _Routine((3,), 13, (4,), 0.8, ("Control valve testing", "Pneumatic line survey", "Review report")),
}
_DEFAULT_ROUTINE = _Routine((0, 1, 2, 3, 4), 9, (1, 2, 3), 0.3, tuple(_HEATING_TASKS))


def _calendar_entry(project: Project, routine: _Routine, day: date, rng: random.Random) -> ics.Event:
    """One day's work on *project*: a few hours, or the whole day on site."""
    task = rng.choice(routine.tasks)
    event = ics.Event(name=f"{task} {project.tag}", description=f"{task} for {project.title}")
    if routine.hours:
        begin = datetime.datetime.combine(day, datetime.time(routine.start_hour), tzinfo=_CET)
        event.begin = begin
        event.end = begin + timedelta(hours=rng.choice(routine.hours))
    else:
        event.begin = day
        event.make_all_day()
    return event


def create_fake_calendar(project_list: List[Project], today: Optional[date] = None) -> ics.Calendar:
    """Harry's work calendar: everything he has worked so far, and the next two weeks.

    Each project follows its routine in ``_DEMO_ROUTINES`` between its start
    and end date. Emergencies are only in the calendar once they happened, and
    leads and offers not at all. One appointment carries no project tag, as in
    any real calendar, so Time Tracking asks about it.
    """
    rng = random.Random(_DEMO_SEED)
    calendar = ics.Calendar()
    today = today or date.today()
    horizon = today + timedelta(days=14)
    for project in sorted(project_list, key=lambda p: p.tag):
        if project.stage in ("Lead", "Offer"):
            continue
        routine = _DEMO_ROUTINES.get(project.tag, _DEFAULT_ROUTINE)
        day = max(project.start_date, _month_start(today, 18))
        last = min(horizon if routine.planned_ahead else today, project.end_date or horizon)
        while day <= last:
            if day.weekday() in routine.weekdays and rng.random() < routine.chance:
                calendar.events.add(_calendar_entry(project, routine, day, rng))
            day += timedelta(days=1)

    meeting = datetime.datetime.combine(_add_workdays(today, -4), datetime.time(12), tzinfo=_CET)
    calendar.events.add(
        ics.Event(name="Bloody paperwork with the accountant", begin=meeting, end=meeting + timedelta(hours=1))
    )
    return calendar


def _invoice_numbers() -> Callable[[date], str]:
    """Invoice numbers in the app's default scheme: the date and a sequence number for the day."""
    issued: Counter = Counter()

    def number(day: date) -> str:
        issued[day] += 1
        return f"{day:%Y-%m-%d}-{issued[day]:02d}"

    return number


def _billing_periods(start: date, months: int, today: date, workdays_after: int) -> Iterator[tuple[date, date, date]]:
    """First day, last day and invoice date of each *months*-month period from *start* invoiced by *today*.

    A period is invoiced *workdays_after* weekdays after it ends.
    """
    while True:
        end = _month_start(start, -months) - timedelta(days=1)
        invoice_date = _add_workdays(end, workdays_after)
        if invoice_date > today:
            return
        yield start, end, invoice_date
        start = end + timedelta(days=1)


def _bill_tracked_time(
    time_data: DataFrame,
    project: Project,
    start: date,
    end: date,
    invoice_date: date,
    number: Callable[[date], str],
    charges: Optional[List[ContractCharge]] = None,
) -> Optional[Invoice]:
    """Invoice the time tracked on *project* from *start* to *end*, with its timesheet, as Create Invoice does."""
    try:
        timesheet = timetracking.generate_timesheet(time_data, project, start, end, date=invoice_date)
    except ValueError:
        return None  # nothing tracked in that period
    invoice = invoicing.generate_invoice(
        timesheets=[timesheet],
        contract=project.contract,
        project=project,
        number=number(invoice_date),
        date=invoice_date,
        charges=charges,
    )
    timesheet.invoice = invoice
    return invoice


def _copy_items(invoice: Invoice, extra: float = 0) -> List[InvoiceItem]:
    """New items like those of *invoice*, each with *extra* added to its quantity."""
    return [
        InvoiceItem(
            start_date=item.start_date,
            end_date=item.end_date,
            quantity=item.quantity + extra,
            unit=item.unit,
            unit_price=item.unit_price,
            description=item.description,
            VAT_rate=item.VAT_rate,
            VAT_category=item.VAT_category,
            contract_charge=item.contract_charge,
        )
        for item in invoice.items
    ]


def _send(invoice: Invoice, today: date, paid: Optional[bool] = None) -> Invoice:
    """Mark *invoice* sent on its date, and paid once it is due unless *paid* says otherwise."""
    invoice.sent = True
    invoice.sent_date = invoice.date
    invoice.paid = invoice.due_date < today if paid is None else paid
    return invoice


def _remind(invoice: Invoice, on: date, fee: Decimal) -> Invoice:
    """A first payment reminder for *invoice*, sent *on* that day with two more weeks to pay."""
    return Invoice(
        document_type="reminder",
        number=invoice.number,
        date=on,
        contract=invoice.contract,
        project=invoice.project,
        reminder_for=invoice,
        reminder_level=1,
        reminder_fee=fee,
        reminder_due_date=on + timedelta(days=14),
        sent=True,
        sent_date=on,
        items=_copy_items(invoice),
    )


def create_demo_invoices(projects: Dict[str, Project], time_data: DataFrame, today: date) -> List[Invoice]:
    """Harry's invoices, built from his calendar the way the app builds them.

    Invoices are paid once they are due, except those that show the rest of
    the workflow: an overdue invoice with a payment reminder, an overdue one
    still waiting for its reminder, a cancelled invoice and its correction, a
    draft, deposits and a final invoice.
    """
    number = _invoice_numbers()
    invoices: List[Invoice] = []

    maintenance = projects["#heatingengineering"]
    for start, end, on in _billing_periods(maintenance.start_date, 3, today, workdays_after=2):
        if invoice := _bill_tracked_time(time_data, maintenance, start, end, on, number):
            invoices.append(_send(invoice, today))

    # Shangri-La Towers' invoices close with a saved note. The invoice of two
    # months ago is unpaid, and a reminder has gone out.
    emergency = projects["#emergency"]
    for start, end, on in _billing_periods(emergency.start_date, 1, today, workdays_after=1):
        if not (invoice := _bill_tracked_time(time_data, emergency, start, end, on, number)):
            continue
        invoice.notes = _DEMO_INVOICE_NOTES[1]
        if start == _month_start(today, 2):
            invoices += [_send(invoice, today, paid=False), _remind(invoice, today - timedelta(days=9), Decimal("5"))]
        else:
            invoices.append(_send(invoice, today))

    retrofit = projects["#boilerretrofit"]
    periods = list(_billing_periods(retrofit.start_date, 1, today, workdays_after=3))
    for k, (start, end, on) in enumerate(periods):
        corrected = k == 1 and k < len(periods) - 1
        # The one-off survey fee goes on the first invoice only.
        charges = list(retrofit.contract.charges) if k == 0 else None
        invoice_date = _add_workdays(on, 3) if corrected else on
        if not (invoice := _bill_tracked_time(time_data, retrofit, start, end, invoice_date, number, charges)):
            continue
        invoice.notes = _DEMO_INVOICE_NOTES[1]
        if k == len(periods) - 1:
            # Last month's invoice is a draft, not sent yet.
            invoices.append(invoice)
            continue
        if corrected:
            # First sent with two days too many, cancelled and sent again.
            invoices.append(
                Invoice(
                    number=number(on),
                    date=on,
                    contract=invoice.contract,
                    project=invoice.project,
                    sent=True,
                    sent_date=on,
                    cancelled=True,
                    notes=invoice.notes,
                    items=_copy_items(invoice, extra=2),
                )
            )
        invoices.append(_send(invoice, today))

    duct_review = projects["#ductcontrol"]
    for start, end, on in _billing_periods(duct_review.start_date, 1, today, workdays_after=4):
        if invoice := _bill_tracked_time(time_data, duct_review, start, end, on, number):
            invoices.append(_send(invoice, today))

    # The first instalment of the modernisation, paid.
    modernisation = projects["#modernisation"]
    first = modernisation.contract.payment_milestones[0]
    deposit_date = modernisation.start_date + timedelta(days=10)
    deposit = invoicing.generate_deposit_invoice(
        contract=modernisation.contract,
        project=modernisation,
        milestone=first,
        number=number(deposit_date),
        date=deposit_date,
    )
    deposit.milestone = first
    first.invoiced = True
    invoices.append(_send(deposit, today, paid=True))

    # Sam Lowry paid the deposit. The final invoice states the full price,
    # deducts the deposit, and is overdue, with no reminder yet: a task asks
    # for one.
    repair = projects["#heatingrepair"]
    deposit_date = repair.start_date + timedelta(days=3)
    deposit = invoicing.generate_deposit_invoice(
        contract=repair.contract,
        project=repair,
        milestone=repair.contract.payment_milestones[0],
        number=number(deposit_date),
        date=deposit_date,
    )
    deposit.milestone = repair.contract.payment_milestones[0]
    final_date = today - timedelta(days=21)
    final = invoicing.generate_final_invoice(
        contract=repair.contract,
        project=repair,
        deposit_invoices=[deposit],
        number=number(final_date),
        date=final_date,
    )
    for milestone in repair.contract.payment_milestones:
        milestone.invoiced = True
    invoices += [_send(deposit, today, paid=True), _send(final, today, paid=False)]

    inspection = projects["#ductinspection"]
    inspection_date = inspection.end_date + timedelta(days=3)
    invoices.append(
        _send(
            Invoice(
                number=number(inspection_date),
                date=inspection_date,
                contract=inspection.contract,
                project=inspection,
                items=[
                    InvoiceItem(
                        start_date=inspection.start_date,
                        end_date=inspection.end_date,
                        quantity=inspection.contract.volume,
                        unit="hour",
                        unit_price=inspection.contract.rate,
                        description="Duct inspection",
                        VAT_rate=inspection.contract.VAT_rate,
                    )
                ],
            ),
            today,
            paid=True,
        )
    )

    return invoices


def create_demo_expenses() -> List[RecurringExpense]:
    """What Harry's business costs him: fixed and income-dependent, tax-deductible and not."""
    return [
        # A share of income charged between a floor and a ceiling, like German
        # statutory health insurance for the self-employed.
        RecurringExpense(
            title="Health and care insurance",
            category="health",
            amount=Decimal("0"),
            rate=Decimal("20.5"),
            min_base=Decimal("1318.33"),
            max_base=Decimal("5812.50"),
            period=Cycle.monthly,
            tax_deductible=True,
        ),
        RecurringExpense(
            title="Private pension plan",
            category="pension",
            amount=Decimal("400"),
            period=Cycle.monthly,
        ),
        RecurringExpense(
            title="Liability insurance for heating work",
            category="insurance",
            amount=Decimal("480"),
            period=Cycle.yearly,
            tax_deductible=True,
        ),
        RecurringExpense(
            title="Service van running costs",
            category="operating",
            amount=Decimal("420"),
            period=Cycle.monthly,
            tax_deductible=True,
        ),
        RecurringExpense(
            title="Accountant for the 27B/6 forms",
            category="professional",
            amount=Decimal("350"),
            period=Cycle.quarterly,
            tax_deductible=True,
        ),
        # Billed in dollars, converted at the month's exchange rate.
        RecurringExpense(
            title="Boiler diagnostics software",
            category="operating",
            amount=Decimal("39"),
            currency="USD",
            period=Cycle.monthly,
            tax_deductible=True,
        ),
    ]


def create_demo_goals(today: date) -> List[FinancialGoal]:
    """Revenue targets for this year: one on its way, one already reached."""
    return [
        FinancialGoal(
            title="Yearly revenue",
            target_amount=Decimal("120000.00"),
            target_date=today.replace(month=12, day=31),
        ),
        FinancialGoal(
            title="Workshop tool upgrade",
            target_amount=Decimal("8000.00"),
            target_date=today.replace(month=12, day=31),
        ),
    ]


def create_demo_manual_entries(today: date) -> List[TimeTrackingItem]:
    """Time logged in Tuttle rather than in the calendar: a time slot, and an amount of time on a day."""
    # Stored as wall-clock time in CET, like entries made in the app.
    slot = datetime.datetime.combine(_add_workdays(today, -1), datetime.time(12, 15))
    day = datetime.datetime.combine(_add_workdays(today, -2), datetime.time(0))
    return [
        TimeTrackingItem(
            begin=slot,
            end=slot + timedelta(minutes=30),
            duration=timedelta(minutes=30),
            title="Phone triage: no hot water",
            tag="#emergency",
            description="",
        ),
        TimeTrackingItem(
            begin=day,
            end=day + timedelta(minutes=90),
            duration=timedelta(minutes=90),
            title="Ordering spare parts",
            tag="#heatingengineering",
            description="",
            duration_only=True,
        ),
    ]


def create_demo_task_rules(session: Session, today: datetime.date) -> None:
    """Harry's own task rules, besides the two every user starts with.

    One of each kind: repeating and one-off dates, a status change that has
    already produced a task, one that is only watching, a rule for one client,
    and a paused one.
    """

    def made(days_ago: int) -> datetime.datetime:
        return datetime.datetime.combine(today - timedelta(days=days_ago), datetime.time(9))

    first_of_month = today.replace(day=1)
    renewal = date(today.year if today.month < 12 else today.year + 1, 12, 1)
    rules = [
        TaskRule(
            title="Send invoices for {period}",
            kind="date",
            start_date=first_of_month,
            unit="month",
            created_at=made((today - first_of_month).days + 1),
        ),
        TaskRule(
            title="File the VAT return for {period}",
            note="Due by the 10th of the month after the quarter.",
            kind="date",
            start_date=date(today.year, 1, 10),
            unit="month",
            every=3,
            created_at=made((today - date(today.year, 1, 1)).days),
        ),
        TaskRule(
            title="Renew the professional liability insurance",
            note="The policy runs out at the end of the year.",
            kind="date",
            start_date=renewal,
            created_at=made(20),
        ),
        TaskRule(
            title="Follow up on the offer for {project}",
            kind="event",
            event="project=Offer",
            offset=1,
            offset_unit="week",
            created_at=made(30),
        ),
        TaskRule(
            title="Ask {client} for feedback on {project}",
            kind="event",
            event="project=Completed",
            created_at=made(30),
        ),
        TaskRule(
            title="Invoice {contract} for the period ending {date}",
            kind="event",
            event="contract.period_end",
            paused=True,
            created_at=made(30),
        ),
    ]
    central_services = session.exec(select(Client).where(Client.name == "Central Services")).first()
    if central_services:
        rules[4].client_id = central_services.id
    for rule in rules:
        session.add(rule)
    session.flush()

    # The offer went out nine days ago, so its follow-up is due. Projects
    # already completed when the feedback rule was made get no task.
    for project in session.exec(select(Project)).all():
        stage = project.board_stage(today)
        if stage == "Offer":
            session.add(TaskRuleNotice(rule_id=rules[3].id, subject_id=project.id, noticed_on=today - timedelta(days=9)))
        if stage == "Completed" and (not central_services or project.client and project.client.id == central_services.id):
            session.add(TaskRuleNotice(rule_id=rules[4].id, subject_id=project.id, noticed_on=today, already=True))


def _render_demo_documents(user: User, invoice: Invoice, language: str, template: str):
    """Render *invoice* and its timesheet to PDF, in the client's language if it has one."""
    language = invoice.contract.client.language or language
    try:
        rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=get_data_dir() / "Invoices",
            template_name=template,
            only_final=True,
            language=language,
            include_signature=True,
        )
        for timesheet in invoice.timesheets:
            rendering.render_timesheet(
                user=user,
                timesheet=timesheet,
                out_dir=get_data_dir() / "Timesheets",
                only_final=True,
                language=language,
            )
    except Exception as ex:
        logger.warning(f"Could not render demo invoice {invoice.number}: {ex}")


def install_demo_data(
    db_path: str,
    on_cache_timetracking_dataframe: Callable[[DataFrame], None],
    invoice_language: str = "en",
    invoice_template: str = "invoice-modern",
):
    """
    Install the Harry Tuttle demo in the database.

    Args:
    db_path (str): The path to the database.
    on_cache_timetracking_dataframe (Callable): Called with the demo calendar's
        time tracking data, to store it as the demo user's.
    invoice_language (str): Language of documents for clients without one of their own.
    invoice_template (str): Template to render the invoices with.
    """
    db_url = f"""sqlite:///{db_path}"""
    logger.info(f"Installing demo data in {db_url}...")
    ensure_schema(db_url)
    db_engine = create_engine(db_url)
    today = date.today()

    user = create_demo_user()
    projects, client_contacts = create_demo_business(user, today)

    logger.info("Creating the demo calendar...")
    calendar = ICSCalendar(name="Demo calendar", ics_calendar=create_fake_calendar(list(projects.values())))
    time_data = calendar.to_data()
    on_cache_timetracking_dataframe(time_data)

    invoices = create_demo_invoices(projects, time_data, today)

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(user)
        session.add_all(projects.values())
        session.add_all(client_contacts)
        session.add_all(invoices)
        session.add_all(create_demo_expenses())
        session.add_all(InvoiceNote(text=text) for text in _DEMO_INVOICE_NOTES)
        session.add_all(create_demo_goals(today))
        session.add_all(create_demo_manual_entries(today))
        session.commit()

        logger.info(f"Rendering {len(invoices)} demo invoices...")
        for invoice in invoices:
            _render_demo_documents(user, invoice, invoice_language, invoice_template)
        session.commit()

    logger.info("Adding task rules...")
    with Session(db_engine) as session:
        create_demo_task_rules(session, today)
        session.commit()

    db_engine.dispose()
    logger.info("Demo data installed.")
