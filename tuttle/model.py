"""Object model."""

from typing import Optional, List

from sqlmodel import Field, Relationship
from sqlmodel import SQLModel
from pydantic import EmailStr
from decimal import Decimal

from money.money import Money
from money.currency import Currency

from delorean import Delorean as Time
from datetime import timedelta as Timespan


class PersistentObject(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)


class User(PersistentObject):
    name: str


class Account(PersistentObject):
    name: str
    number: str
    owner: User


class Contact(PersistentObject):
    """An entry in the address book."""

    name: str
    e_mail: Optional[EmailStr]


class Client(Contact):
    """A client the freelancer has contracted with."""

    contracts: List["Contract"] = Relationship(back_populates="client")


class Rate(SQLModel):
    amount: Decimal
    currency: Currency
    timespan: Timespan


class Contract(PersistentObject):
    client: Client = Relationship(back_populates="contracts")
    # rate: Optional[Rate]
    projects: List["Project"] = Relationship(back_populates="contract")


class Project(PersistentObject):
    """A project is a group of contract work for a client."""

    name: str
    contract: Contract = Relationship(back_populates="projects")


class Timesheet(SQLModel):
    pass


class Invoice(PersistentObject):
    contract: Contract
    timesheet: Timesheet


class Payment(SQLModel):
    invoice: Invoice


if __name__ == "__main__":

    central_services = Client(
        name="Central Services", e_mail="info@centralservices.com"
    )

    my_contract = Contract(
        client=central_services,
    )

    my_project = Project(name="Ducts", contract=my_contract)

    print(central_services.contracts)
