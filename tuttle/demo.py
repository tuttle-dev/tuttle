from typing import Callable, List, Optional

import datetime
import random
from datetime import date, timedelta
from pathlib import Path
from decimal import Decimal

import faker
import ics
import numpy
import sqlalchemy
from loguru import logger
from sqlmodel import Field, Session, SQLModel, create_engine, select

from tuttle import rendering
from tuttle.calendar import Calendar, ICSCalendar
from tuttle.model import (
    Address,
    BankAccount,
    Client,
    Contact,
    Contract,
    Cycle,
    Invoice,
    InvoiceItem,
    Timesheet,
    TimeTrackingItem,
    Project,
    TimeUnit,
    User,
)


def create_fake_user(
    fake: faker.Faker,
) -> User:
    """
    Create a fake user.
    """
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
        # TODO: This has a German bias
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


def create_fake_client(
    fake: faker.Faker,
    invoicing_contact: Optional[Contact] = None,
) -> Client:
    if invoicing_contact is None:
        invoicing_contact = create_fake_contact(fake)
    client = Client(
        name=fake.company(),
        invoicing_contact=invoicing_contact,
    )
    assert client.invoicing_contact is not None
    return client


def create_fake_contract(
    fake: faker.Faker,
    client: Optional[Client] = None,
) -> Contract:
    """
    Create a fake contract for the given client.
    """
    if client is None:
        client = create_fake_client(fake)
    unit = random.choice(list(TimeUnit))
    if unit == TimeUnit.day:
        rate = fake.random_int(200, 1000)  # realistic distribution for day rates
    elif unit == TimeUnit.hour:
        rate = fake.random_int(10, 100)  # realistic distribution for hourly rates
    else:
        rate = fake.random_int(1, 1000)
    return Contract(
        title=f"{client.name} service contract",
        client=client,
        signature_date=fake.date_this_year(before_today=True),
        start_date=fake.date_this_year(after_today=True),
        rate=rate,
        currency="EUR",  # TODO: Use actual currency
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
        title=fake.bs().replace("/", "-"),
        comment=fake.paragraph(nb_sentences=2),
        date=datetime.date.today(),
        period_start=datetime.date.today() - datetime.timedelta(days=30),
        period_end=datetime.date.today(),
        project=project,
    )
    number_of_items = fake.random_int(min=1, max=5)
    for _ in range(number_of_items):
        unit = fake.random_element(elements=("hours", "days"))
        if unit == "hours":
            unit_price = abs(round(numpy.random.normal(50, 20), 2))
        elif unit == "days":
            unit_price = abs(round(numpy.random.normal(400, 200), 2))
        time_tracking_item = TimeTrackingItem(
            timesheet=timesheet,
            begin=fake.date_time_this_year(before_now=True, after_now=False),
            end=fake.date_time_this_year(before_now=True, after_now=False),
            duration=datetime.timedelta(hours=fake.random_int(min=1, max=8)),
            title=f"{fake.bs()} for #{project.tag}",
            tag=project.tag,
            description=fake.paragraph(nb_sentences=2),
        )
        timesheet.items.append(time_tracking_item)
    return timesheet


def create_fake_invoice(
    fake: faker.Faker,
    project: Optional[Project] = None,
    user: Optional[User] = None,
    render: bool = True,
) -> Invoice:
    """
    Create a fake invoice object with random values.

    Args:
    project (Project): The project associated with the invoice.
    fake (faker.Faker): An instance of the Faker class to generate random values.

    Returns:
    Invoice: A fake invoice object.
    """
    if project is None:
        project = create_fake_project(fake)

    if user is None:
        user = create_fake_user(fake)

    invoice_number = (
        f"{datetime.date.today().strftime('%Y-%m-%d')}-{next(invoice_number_counter)}"
    )
    invoice = Invoice(
        number=invoice_number,
        date=datetime.date.today(),
        sent=fake.pybool(),
        paid=fake.pybool(),
        cancelled=fake.pybool(),
        contract=project.contract,
        project=project,
        rendered=fake.pybool(),
    )
    number_of_items = fake.random_int(min=1, max=5)
    for _ in range(number_of_items):
        unit = fake.random_element(elements=("hours", "days"))
        unit_price = 0
        if unit == "hours":
            unit_price = abs(round(numpy.random.normal(50, 20), 2))
        elif unit == "days":
            unit_price = abs(round(numpy.random.normal(500, 200), 2))
        vat_rate = round(numpy.random.uniform(0.05, 0.25), 2)
        invoice_item = InvoiceItem(
            start_date=fake.date_this_decade(),
            end_date=fake.date_this_decade(),
            quantity=fake.random_int(min=1, max=10),
            unit=unit,
            unit_price=Decimal(unit_price),
            description=fake.sentence(),
            VAT_rate=Decimal(vat_rate),
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
                out_dir=Path.home() / ".tuttle" / "Invoices",
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
                out_dir=Path.home() / ".tuttle" / "Timesheets",
                only_final=True,
            )
            logger.info(f"✅ rendered timesheet for {project.title}")
        except Exception as ex:
            logger.error(f"❌ Error rendering timesheet for {project.title}: {ex}")
            logger.exception(ex)

    return invoice


def create_fake_data(
    user: User,
    n: int = 10,
):
    locales = [
        "de_DE",
        "de_CH",
        "de_AT",
        "en_US",
        "en_GB",
        "es_ES",
        "fr_FR",
        "it_IT",
        "sv_SE",
        "cz_CZ",
        "nl_NL",
        "pt_BR",
        "tr_TR",
    ]
    fake = faker.Faker(locale=locales)

    contacts = [create_fake_contact(fake) for _ in range(n)]
    clients = [
        create_fake_client(fake, invoicing_contact=contact) for contact in contacts
    ]
    contracts = [create_fake_contract(fake, client=client) for client in clients]
    projects = [create_fake_project(fake, contract=contract) for contract in contracts]

    invoices = [
        create_fake_invoice(fake, project=project, user=user) for project in projects
    ]

    return projects, invoices


def create_demo_user() -> User:
    user = User(
        name="Harry Tuttle",
        subtitle="Heating Engineer",
        website="https://tuttle-dev.github.io/tuttle/",
        email="mail@tuttle.com",
        phone_number="+55555555555",
        VAT_number="27B-6",
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
    def random_datetime(start, end):
        return start + timedelta(
            seconds=random.randint(0, int((end - start).total_seconds()))
        )

    def random_duration():
        return timedelta(hours=random.randint(1, 8))

    # create a new calendar
    calendar = ics.Calendar()

    # get the last month's date range
    # get todays date
    now = datetime.datetime.now()
    month_ago = now - timedelta(days=30)

    # populate the calendar with events
    for project in project_list:
        # create 1-5 events for each project
        for _ in range(random.randint(1, 5)):
            # create a new event
            event = ics.Event()
            event.name = f"Meeting for {project.tag}"

            # set the event's begin and end datetime
            event.begin = random_datetime(month_ago, now)
            event.end = event.begin + random_duration()

            # add to calendar.events
            calendar.events.add(event)
    return calendar


def install_demo_data(
    n_projects: int,
    db_path: str,
    on_cache_timetracking_dataframe: Optional[Callable] = None,
):
    """
    Install demo data in the database.

    Args:
    n_projects (int): The number of projects to create.
    db_path (str): The path to the database.
    on_cache_timetracking_dataframe (Optional[Callable], optional): A callback function to be called when the timetracking dataframe is cached. Defaults to None.
    """
    db_path = f"""sqlite:///{db_path}"""
    logger.info(f"Installing demo data in {db_path}...")
    logger.info(f"Creating database engine at: {db_path}...")
    db_engine = create_engine(db_path)
    logger.info("Creating database tables...")
    SQLModel.metadata.create_all(db_engine)

    logger.info("Creating demo user...")
    with Session(db_engine) as session:
        user = create_demo_user()
        session.add(user)
        session.commit()
        session.refresh(user)

    logger.info(f"Creating {n_projects} fake projects...")
    projects, invoices = create_fake_data(user, n_projects)

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
    with Session(db_engine) as session:
        for invoice in invoices:
            session.add(invoice)
            session.commit()

    logger.info("Adding fake projects...")
    with Session(db_engine) as session:
        for project in projects:
            session.add(project)
            session.commit()
