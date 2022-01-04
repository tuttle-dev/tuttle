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


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: EmailStr


class BankAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    IBAN: str  # TODO: add type / validator
    BIC: str  # TODO: add type / validator
    BLZ: str  # TODO: add type / validator
    username: str  # online banking user name
    # owner: User


class Contact(SQLModel, table=True):
    """An entry in the address book."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    e_mail: Optional[EmailStr]


class Client(Contact, table=True):
    """A client the freelancer has contracted with."""

    contracts: List["Contract"] = Relationship(back_populates="client")


class Rate(SQLModel):
    amount: Decimal
    currency: Currency
    timespan: Timespan


# class BillingCycle(SQLModel, table=True):
#     """Billing cycle associated with a contract."""
#     id: Optional[int] = Field(default=None, primary_key=True)
#     contracts: List["Contract"] = Relationship(back_populates="billing_cycle")
#     # TODO: billing time
#     # TODO: billing period


class Contract(SQLModel, table=True):
    """A contract defines the business conditions of a project"""

    id: Optional[int] = Field(default=None, primary_key=True)
    # billing_cycle: BillingCycle = Relationship(back_populates="contracts")
    # client: Client = Relationship(back_populates="contracts")
    # rate: Optional[Rate]
    # projects: List["Project"] = Relationship(back_populates="contract")
    # invoices: List["Invoice"] = Relationship(back_populates="contract")


class Project(SQLModel, table=True):
    """A project is a group of contract work for a client."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # contract: Contract = Relationship(back_populates="projects")
    # timesheets: List["Timesheet"] = Relationship(back_populates="project")


class Timesheet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # project: Project = Relationship(back_populates="timesheets")


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # timesheet: Timesheet = Relationship(back_populates="invoice")
    # contract: Contract = Relationship(back_populates="invoices")
    # payment: Optional["Payment"] = Relationship(back_populates="invoice")
    # timesheet: Timesheet =


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # invoice: Invoice = Relationship(back_populates="payment")


if __name__ == "__main__":

    central_services = Client(
        name="Central Services", e_mail="info@centralservices.com"
    )

    my_contract = Contract(client=central_services)

    my_project = Project(name="Ducts", contract=my_contract)

    print(central_services.contracts)
