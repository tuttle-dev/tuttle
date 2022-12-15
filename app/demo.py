from typing import List

import faker
import random
import datetime
from sqlmodel import Field, SQLModel, create_engine, Session, select
import sqlalchemy

from tuttle.model import Address, Contact, Client, Project, Contract, TimeUnit, Cycle

def create_fake_contact(
    fake: faker.Faker,
):
    street_line, city_line = fake.address().splitlines()
    a = Address(
        id=id,
        street=street_line.split(" ")[0],
        number=street_line.split(" ")[1],
        city=city_line.split(" ")[1],
        postal_code=city_line.split(" ")[0],
        country=fake.country(),
    )
    first_name, last_name = fake.name().split(" ", 1)
    contact = Contact(
        id=id,
        first_name=first_name,
        last_name=last_name,
        email=fake.email(),
        company=fake.company(),
        address_id=a.id,
        address=a,
    )
    return contact

def create_fake_client(
    invoicing_contact: Contact,
    fake: faker.Faker,
):
    client = Client(
        id=id,
        name=fake.company(),
        invoicing_contact=invoicing_contact,
    )
    return client


def create_fake_contract(
    client: Client,
    fake: faker.Faker,
) -> Contract:
    """
    Create a fake contract for the given client.
    """
    return Contract(
        title=fake.sentence(),
        client=client,
        signature_date=fake.date_this_year(before_today=True),
        start_date=fake.date_this_year(after_today=True),
        rate=fake.random_int(1, 1000),
        currency="EUR",  # TODO: Use actual currency
        VAT_rate=random.random() * 0.19,
        unit=random.choice(list(TimeUnit)),
        units_per_workday=random.randint(1, 12),
        volume=fake.random_int(1, 1000),
        term_of_payment=fake.random_int(1, 31),
        billing_cycle=random.choice(list(Cycle)),
    )

def create_fake_project(
    contract: Contract,
    fake: faker.Faker, 
):
    project_title = fake.bs()
    project = Project(
        title=project_title,
        tag=project_title.replace(' ', '-').lower(),
        description=fake.paragraph(nb_sentences=2),
        unique_tag=project_title.split(" ")[0].lower(),
        is_completed=fake.pybool(),
        start_date=datetime.date.today(),
        end_date=datetime.date.today() + datetime.timedelta(days=80),
        contract=contract,
    )
    return project



def create_fake_data(
    n: int = 10,
):
    locales = ["de_DE", "en_US", "es_ES", "fr_FR", "it_IT", "sv_SE"]
    fake = faker.Faker()
    contacts = [create_fake_contact(fake) for _ in range(n)]
    clients = [create_fake_client(contact, fake) for contact in contacts]
    contracts = [create_fake_contract(client, fake) for client in clients]
    projects = [create_fake_project(contract, fake) for contract in contracts]
    return projects




def install_demo_data(
    n: int,
):
    projects = create_fake_data(n)
    db_engine = create_engine("sqlite:///")
    SQLModel.metadata.create_all(db_engine)
    with Session(db_engine) as session:
        for project in projects:
            session.add(project)
            session.commit()



if __name__ == "__main__":
    install_demo_data(n=10)
