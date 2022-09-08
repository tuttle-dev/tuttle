import datetime

from tuttle.model import (
    Contact,
    Address,
    User,
    BankAccount,
    Client,
    Contract,
    Project,
)
from tuttle import time, controller

# USERS

user = User(
    name="Harry Tuttle",
    subtitle="Heating Engineer",
    website="https://tuttle-dev.github.io/tuttle/",
    email="mail@tuttle.com",
    phone_number="+55555555555",
    VAT_number="27B-6",
    address=Address(
        name="Harry Tuttle",
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

# CONTACTS

contact_one = Contact(
    name="Sam Lowry",
    email="lowry@centralservices.com",
    address=Address(
        street="Main Street",
        number="9999",
        postal_code="55555",
        city="Somewhere",
        country="Brazil",
    ),
)

contact_two = Contact(
    name="Jill Layton",
    email="jilllayton@gmail.com",
    address=None,
)

contact_three = Contact(
    name="Mr Kurtzman",
    company="Central Services",
    email="kurtzman@centralservices.com",
    address=Address(
        street="Main Street",
        number="1111",
        postal_code="55555",
        city="Somewhere",
        country="Brazil",
    ),
)

contact_four = Contact(
    name="Harry Buttle",
    company="Shoe Repairs Central",
    address=Address(
        street="Main Street",
        number="8888",
        postal_code="55555",
        city="Somewhere",
        country="Brazil",
    ),
)


# CLIENTS

client_one = Client(
    name="Central Services",
    invoicing_contact=Contact(
        name="Central Services",
        email="info@centralservices.com",
        address=Address(
            street="Main Street",
            number="42",
            postal_code="55555",
            city="Somewhere",
            country="Brazil",
        ),
    ),
)

client_two = Client(
    name="Sam Lowry",
    invoicing_contact=contact_one,
)

# CONTRACTS

contract_one = Contract(
    title="Heating Engineering Contract",
    client=client_one,
    rate=100.00,
    currency="EUR",
    unit=time.TimeUnit.hour,
    units_per_workday=8,
    term_of_payment=14,
    billing_cycle=time.Cycle.monthly,
    signature_date=datetime.date(2022, 2, 1),
    start_date=datetime.date(2022, 2, 1),
)

contract_two = Contract(
    title="Heating Repair Contract",
    client=client_two,
    rate=50.00,
    currency="EUR",
    unit=time.TimeUnit.hour,
    units_per_workday=8,
    term_of_payment=14,
    billing_cycle=time.Cycle.monthly,
    signature_date=datetime.date(2022, 1, 1),
    start_date=datetime.date(2022, 1, 1),
)

# PROJECTS

project_one = Project(
    title="Heating Engineering",
    tag="#HeatingEngineering",
    contract=contract_one,
    start_date=datetime.date(2022, 1, 1),
    end_date=datetime.date(2022, 3, 31),
)

project_two = Project(
    title="Heating Repair",
    tag="#HeatingRepair",
    contract=contract_two,
    start_date=datetime.date(2022, 1, 1),
    end_date=datetime.date(2022, 3, 31),
)


def add_demo_content(
    con: controller.Controller,
):
    con.store(user)
    con.store(contact_one)
    con.store(contact_two)
    con.store(contact_three)
    con.store(contact_four)
    con.store(client_one)
    con.store(client_two)
    con.store(contract_one)
    con.store(contract_two)
    con.store(project_one)
    con.store(project_two)


if __name__ == "__main__":
    con = controller.Controller(
        in_memory=True,
    )
    add_demo_content(con)
