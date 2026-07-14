from typing import Callable, List, Optional

import datetime
import random
from datetime import date, timedelta
from pathlib import Path
from decimal import Decimal

import faker
import ics
import numpy
from loguru import logger
from sqlmodel import Session, create_engine

from tuttle import rendering
from tuttle.calendar import Calendar, ICSCalendar
from tuttle.data_dir import get_data_dir
from tuttle.db_schema import ensure_schema

from tuttle.model import (
    Address,
    BankAccount,
    Client,
    ClientContact,
    Contact,
    Contract,
    Cycle,
    FinancialGoal,
    Invoice,
    InvoiceItem,
    TaxCategory,
    Timesheet,
    TimeTrackingItem,
    Project,
    TimeUnit,
    User,
)

# ---------------------------------------------------------------------------
# Curated heating-repair domain data
# ---------------------------------------------------------------------------

_HEATING_CLIENTS = [
    ("Warmwasser Hausverwaltung GmbH", "Property management"),
    ("Centralheating AG", "Heating systems supplier"),
    ("Altbau Wohnungsbau e.G.", "Housing cooperative"),
    ("Stadtwerke Metropolis", "Municipal utilities"),
]

_HEATING_CONTRACTS = [
    "Annual heating maintenance",
    "Boiler service agreement",
    "Emergency repair retainer",
    "Heating system modernisation",
]

_HEATING_PROJECTS = [
    (
        "Boiler replacement Marienstr. 12",
        "Replace ageing gas boiler with modern condensing unit",
    ),
    (
        "Annual inspection Q1",
        "Scheduled safety and efficiency inspection for all units",
    ),
    (
        "Emergency pipe repair Nordblock",
        "Fix burst heating pipe in basement utility room",
    ),
    (
        "Radiator upgrade Westflügel",
        "Swap cast-iron radiators for energy-efficient panel radiators",
    ),
]

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


def create_heating_contact(fake: faker.Faker, company_name: str) -> Contact:
    """Create a contact for a heating-industry client."""
    a = Address(
        street=fake.street_name(),
        number=str(fake.random_int(1, 200)),
        city=fake.city(),
        postal_code=fake.postcode(),
        country="Germany",
    )
    first_name, last_name = fake.name().split(" ", 1)
    return Contact(
        first_name=first_name,
        last_name=last_name,
        email=fake.email(),
        company=company_name,
        address=a,
    )


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
    number_of_items = fake.random_int(min=1, max=4)
    used_items = random.sample(
        _HEATING_INVOICE_ITEMS,
        k=min(number_of_items, len(_HEATING_INVOICE_ITEMS)),
    )
    contract = project.contract
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


def create_usd_security_data(user: User) -> tuple[Project, Invoice, ClientContact]:
    """A US client billed in USD — the mixed-currency case, end to end."""
    contact = Contact(
        first_name="Dana",
        last_name="Reyes",
        email="reyes@ductworksecurity.com",
        company="Ductwork Security Inc.",
        address=Address(
            street="Market Street",
            number="1200",
            postal_code="94103",
            city="San Francisco",
            country="United States",
        ),
    )
    client = Client(name="Ductwork Security Inc.", invoicing_contact=contact)

    contract = Contract(
        title="IT Security Review – Ductwork Security Inc.",
        client=client,
        signature_date=datetime.date.today() - timedelta(days=120),
        start_date=datetime.date.today() - timedelta(days=110),
        rate=Decimal("1000.00"),
        currency="USD",
        # Outside the scope of German VAT: B2B service to a non-EU recipient.
        VAT_rate=Decimal("0"),
        VAT_category=TaxCategory.outside_scope,
        unit=TimeUnit.day,
        units_per_workday=8,
        volume=10,
        term_of_payment=14,
        billing_cycle=Cycle.monthly,
    )

    project = Project(
        title="IT Security Review",
        tag="#itsecurity",
        description="Security review of the pneumatic ductwork control systems",
        is_completed=False,
        start_date=contract.start_date,
        end_date=datetime.date.today() + timedelta(days=60),
        contract=contract,
    )

    inv_date = datetime.date.today() - timedelta(days=45)
    invoice = Invoice(
        number=f"{inv_date.strftime('%Y-%m-%d')}-{next(invoice_number_counter)}",
        date=inv_date,
        sent=True,
        paid=True,
        cancelled=False,
        contract=contract,
        project=project,
        rendered=True,
    )
    InvoiceItem(
        start_date=inv_date - timedelta(days=30),
        end_date=inv_date - timedelta(days=2),
        quantity=1,
        unit="unit",
        unit_price=Decimal("1000.00"),
        description="IT security review",
        VAT_rate=Decimal("0"),
        VAT_category=TaxCategory.outside_scope,
        invoice=invoice,
    )

    try:
        rendering.render_invoice(
            user=user,
            invoice=invoice,
            out_dir=get_data_dir() / "Invoices",
            only_final=True,
        )
        logger.info("✅ rendered USD invoice for IT Security Review")
    except Exception as ex:
        logger.error(f"❌ Error rendering USD invoice: {ex}")

    return (
        project,
        invoice,
        ClientContact(client=client, contact=contact, role="invoicing"),
    )


def create_heating_data(
    user: User,
    n: int = 4,
):
    """Create heating-repair themed demo data for Harry Tuttle."""
    fake = faker.Faker(locale=["de_DE", "en_US"])

    # -- canonical clients (always present) ------------------------------------

    central_services = Client(
        name="Central Services",
        vat_number="BR12345678901",
        address=Address(
            street="Main Street",
            number="42",
            postal_code="55555",
            city="Somewhere",
            country="Brazil",
        ),
    )

    sam_lowry_contact = Contact(
        first_name="Sam",
        last_name="Lowry",
        email="lowry@centralservices.com",
        address=Address(
            street="Main Street",
            number="9999",
            postal_code="55555",
            city="Somewhere",
            country="Brazil",
        ),
    )
    sam_lowry = Client(name="Sam Lowry", invoicing_contact=sam_lowry_contact)

    # Extra contact shared across multiple clients
    central_services_accountant = Contact(
        first_name="Jill",
        last_name="Layton",
        email="layton@centralservices.com",
        company="Central Services",
        address=Address(
            street="Main Street",
            number="42",
            postal_code="55555",
            city="Somewhere",
            country="Brazil",
        ),
    )

    # Archibald Buttle — wrongly arrested instead of Tuttle
    archibald_buttle = Contact(
        first_name="Archibald",
        last_name="Buttle",
        email="buttle@centralservices.com",
        address=Address(
            street="Shangri-La Towers",
            number="412",
            postal_code="55555",
            city="Somewhere",
            country="Brazil",
        ),
    )

    contacts = [sam_lowry_contact, central_services_accountant, archibald_buttle]
    clients = [central_services, sam_lowry]

    # Many-to-many: contacts ↔ clients with roles
    client_contacts = [
        ClientContact(
            client=central_services, contact=sam_lowry_contact, role="project lead"
        ),
        ClientContact(
            client=central_services,
            contact=central_services_accountant,
            role="accountant",
        ),
        ClientContact(
            client=central_services, contact=archibald_buttle, role="shoe repair"
        ),
        ClientContact(client=sam_lowry, contact=sam_lowry_contact, role="invoicing"),
    ]

    # -- randomly generated heating-industry clients ---------------------------

    n = min(n, len(_HEATING_CLIENTS))
    for i in range(n):
        name, _desc = _HEATING_CLIENTS[i]
        contact = create_heating_contact(fake, company_name=name)
        contacts.append(contact)
        vat_number = f"DE{fake.unique.random_number(digits=9, fix_len=True)}"
        client = Client(name=name, vat_number=vat_number, invoicing_contact=contact)
        clients.append(client)
        client_contacts.append(
            ClientContact(client=client, contact=contact, role="invoicing")
        )

    # -- contracts (one per client) --------------------------------------------

    contracts = []
    for i, client in enumerate(clients):
        if client is sam_lowry:
            rate = 0
            title = "Heating Repair"
        else:
            rate = random.choice([65, 72, 80, 85, 95])
            title = _HEATING_CONTRACTS[i % len(_HEATING_CONTRACTS)]
        contract = Contract(
            title=f"{title} – {client.name}",
            client=client,
            signature_date=fake.date_between(start_date="-30M", end_date="-24M"),
            start_date=fake.date_between(start_date="-24M", end_date="-20M"),
            rate=rate,
            currency="EUR",
            VAT_rate=Decimal("0.19"),
            unit=TimeUnit.hour,
            units_per_workday=8,
            volume=random.randint(100, 400),
            term_of_payment=14,
            billing_cycle=Cycle.monthly,
        )
        contracts.append(contract)

    _CANONICAL_PROJECTS = {
        "Central Services": (
            "Heating Engineering",
            "Central heating system maintenance and engineering",
        ),
        "Sam Lowry": (
            "Heating Repair",
            "Emergency heating repair for a friend",
        ),
    }

    projects = []
    for i, contract in enumerate(contracts):
        canonical = _CANONICAL_PROJECTS.get(contract.client.name)
        if canonical:
            title, description = canonical
        else:
            title, description = _HEATING_PROJECTS[i % len(_HEATING_PROJECTS)]
        tag = f"#{''.join(title.split()[:2]).lower()}"
        project = Project(
            title=title,
            tag=tag,
            description=description,
            is_completed=False,
            start_date=contract.start_date,
            end_date=datetime.date.today() + datetime.timedelta(days=180),
            contract=contract,
        )
        projects.append(project)

    # -- one US client invoiced in USD ----------------------------------------
    # Harry is taxed in Germany but bills this one in dollars: the mixed-currency
    # case. B2B to a non-EU recipient, so the supply is outside the scope of
    # German VAT (§ 3a Abs. 2 UStG).
    us_project, us_invoice, us_client_contact = create_usd_security_data(user)
    projects.append(us_project)
    client_contacts.append(us_client_contact)

    today = datetime.date.today()
    invoices = [us_invoice]
    for i, project in enumerate(projects[:-1]):
        if i < 2:
            # First two invoices: sent but unpaid, dated 30+ days ago → overdue
            inv_date = today - timedelta(days=random.randint(30, 60))
            inv = create_fake_invoice(
                fake,
                project=project,
                user=user,
                invoice_date=inv_date,
                sent=True,
                paid=False,
            )
        else:
            inv = create_fake_invoice(fake, project=project, user=user)
        invoices.append(inv)
    return projects, invoices, client_contacts


def create_fake_data(
    user: User,
    n: int = 10,
):
    """Legacy entry point — delegates to heating-themed generator."""
    return create_heating_data(user, n=n)


def create_historical_invoices(
    fake: faker.Faker,
    projects: List[Project],
    user: User,
    n_months: int = 11,
) -> List[Invoice]:
    """Create invoices spread across the past n_months for dashboard history."""
    today = datetime.date.today()
    invoices = []
    for months_ago in range(n_months, 0, -1):
        # First day of that month
        inv_date = (today - timedelta(days=30 * months_ago)).replace(day=15)
        # Pick 1-2 random projects to invoice each month
        month_projects = random.sample(
            projects, k=min(random.randint(1, 2), len(projects))
        )
        for project in month_projects:
            inv = create_fake_invoice(
                fake,
                project=project,
                user=user,
                render=True,
                invoice_date=inv_date,
                paid=True,
                sent=True,
                cancelled=False,
            )
            invoices.append(inv)
    return invoices


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
        VAT_number="27B-6",
        signature=_load_demo_signature(),
        address=Address(
            street="Main Street",
            number="450",
            city="Somewhere",
            postal_code="555555",
            country="Brazil",
        ),
        bank_account=BankAccount(
            name="Giro",
            IBAN="BZ99830994950003161565",
            BIC="BANKINFO101",
        ),
    )
    return user


def create_fake_calendar(project_list: List[Project]) -> ics.Calendar:
    """Generate a realistic work calendar spanning the last ~3 months.

    Events land on weekdays during business hours (8–18), with varied
    durations (1–6 h) and descriptive titles including the project tag.
    """
    calendar = ics.Calendar()
    today = datetime.date.today()
    start_date = today - timedelta(days=90)

    task_verbs = [
        "Work on",
        "Review",
        "Planning",
        "Development",
        "Meeting",
        "Testing",
        "Documentation",
        "Research",
        "Sprint review",
    ]

    for project in project_list:
        current = start_date
        while current <= today:
            if current.weekday() < 5:  # weekdays only
                if random.random() < 0.45:  # ~45 % chance per weekday
                    start_hour = random.choice([8, 9, 10, 13, 14, 15])
                    duration_h = random.choice([1, 2, 2, 3, 3, 4, 6])
                    begin = datetime.datetime(
                        current.year,
                        current.month,
                        current.day,
                        start_hour,
                        random.choice([0, 15, 30]),
                    )
                    event = ics.Event()
                    verb = random.choice(task_verbs)
                    event.name = f"{verb} {project.tag}"
                    event.begin = begin
                    event.end = begin + timedelta(hours=duration_h)
                    event.description = f"{verb} for {project.title}"
                    calendar.events.add(event)
            current += timedelta(days=1)
    return calendar


def install_demo_data(
    n_projects: int,
    db_path: str,
    on_cache_timetracking_dataframe: Optional[Callable] = None,
    invoice_language: str = "en",
    invoice_template: str = "invoice-modern",
):
    """
    Install demo data in the database.

    Args:
    n_projects (int): The number of projects to create.
    db_path (str): The path to the database.
    on_cache_timetracking_dataframe (Optional[Callable], optional): A callback function
        to be called when the timetracking dataframe is cached. Defaults to None.
    """
    db_url = f"""sqlite:///{db_path}"""
    logger.info(f"Installing demo data in {db_url}...")
    ensure_schema(db_url)
    db_engine = create_engine(db_url)

    logger.info("Creating demo user...")
    with Session(db_engine) as session:
        user = create_demo_user()
        session.add(user)
        session.commit()
        session.refresh(user)

    logger.info(f"Creating {n_projects} fake projects...")
    projects, invoices, client_contacts = create_fake_data(user, n_projects)

    # create a fake calendar and add time tracking data from it
    logger.info("Creating a fake calendar...")
    calendar: Calendar = ICSCalendar(
        name="Demo calendar",
        ics_calendar=create_fake_calendar(project_list=projects),
    )
    time_tracking_data = calendar.to_data()
    logger.info("Caching timetracking data")
    on_cache_timetracking_dataframe(time_tracking_data)
    logger.info("Demo data installed.")

    # add fake invoices
    logger.info("Adding fake invoices...")
    from .rendering import render_invoice
    from pathlib import Path

    out_dir = get_data_dir() / "Invoices"

    with Session(db_engine, expire_on_commit=False) as session:
        for invoice in invoices:
            session.add(invoice)
        session.commit()

        # add historical invoices in the same session so relationships resolve
        logger.info("Adding historical invoices...")
        locales = ["de_DE", "en_US", "en_GB", "fr_FR"]
        fake = faker.Faker(locale=locales)
        historical_invoices = create_historical_invoices(
            fake, projects, user, n_months=24
        )
        for invoice in historical_invoices:
            session.add(invoice)
        session.commit()

        # add projects in the same session
        logger.info("Adding fake projects...")
        for project in projects:
            session.merge(project)
        session.commit()

        # add client-contact many-to-many associations
        logger.info("Adding client-contact associations...")
        for cc in client_contacts:
            session.merge(cc)
        session.commit()

        # render all invoices to PDF while objects are still session-bound
        logger.info("Rendering demo invoices...")
        all_invoices = invoices + historical_invoices
        for inv in all_invoices:
            try:
                render_invoice(
                    user=user,
                    invoice=inv,
                    out_dir=out_dir,
                    template_name=invoice_template,
                    only_final=True,
                    language=invoice_language,
                    include_signature=True,
                )
            except Exception as ex:
                logger.warning(f"Could not render demo invoice {inv.number}: {ex}")

    logger.info("Adding financial goals...")
    with Session(db_engine) as session:
        today = datetime.date.today()
        goals = [
            FinancialGoal(
                title="Service van replacement fund",
                target_amount=Decimal("35000.00"),
                target_date=today.replace(year=today.year + 1, month=3, day=31),
            ),
            FinancialGoal(
                title="Workshop tool upgrade",
                target_amount=Decimal("8000.00"),
                target_date=today.replace(month=12, day=31),
            ),
        ]
        for goal in goals:
            session.add(goal)
        session.commit()

    db_engine.dispose()
