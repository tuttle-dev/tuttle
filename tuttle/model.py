"""Object model."""

import email
from typing import Optional, List, Dict, Type
from pydantic import constr, BaseModel, condecimal
from enum import Enum
import datetime
import hashlib
import uuid
import textwrap

import sqlalchemy
from sqlmodel import (
    SQLModel,
    Field,
    Relationship,
)

# from pydantic import str
import decimal
from decimal import Decimal
import pandas


from .time import Cycle, TimeUnit

from .dev import deprecated


def help(model_class):
    return pandas.DataFrame(
        (
            (field_name, field.field_info.description)
            for field_name, field in Contract.__fields__.items()
        ),
        columns=["field name", "field description"],
    )


def to_dataframe(items: List[Type[BaseModel]]) -> pandas.DataFrame:
    """Convert list of pydantic model items to DataFrame.

    Args:
        items (List[Type[BaseModel]]): [description]

    Returns:
        pandas.DataFrame: [description]
    """
    return pandas.DataFrame.from_records([item.dict() for item in items])


def OneToOneRelationship(back_populates):
    return Relationship(
        back_populates=back_populates,
        sa_relationship_kwargs={"uselist": False},
    )


class Address(SQLModel, table=True):
    """Postal address."""

    id: Optional[int] = Field(default=None, primary_key=True)
    # name: str
    street: str = Field(default="")
    number: str = Field(default="")
    city: str = Field(default="")
    postal_code: str = Field(default="")
    country: str = Field(default="")
    users: List["User"] = Relationship(back_populates="address")
    contacts: List["Contact"] = Relationship(back_populates="address")

    @property
    def printed(self):
        """Print address in common format."""
        return textwrap.dedent(
            f"""
        {self.street} {self.number}
        {self.postal_code} {self.city}
        {self.country}
        """
        )

    @property
    def html(self):
        """Print address in common format."""
        return textwrap.dedent(
            f"""
        {self.street} {self.number}<br>
        {self.postal_code} {self.city}<br>
        {self.country}
        """
        )

    @property
    def is_empty(self) -> bool:
        """True if all fields are empty."""
        return all(
            [
                not self.street,
                not self.number,
                not self.city,
                not self.postal_code,
                not self.country,
            ]
        )


class User(SQLModel, table=True):
    """User of the application, a freelancer."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    subtitle: str
    website: Optional[str]
    email: str
    phone_number: Optional[str]
    profile_photo_path: Optional[str] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="address.id")
    address: Optional[Address] = Relationship(
        back_populates="users", sa_relationship_kwargs={"lazy": "subquery"}
    )
    VAT_number: str = Field(
        description="Value Added Tax number of the user, legally required for invoices.",
    )
    # User 1:1* ICloudAccount
    icloud_account_id: Optional[int] = Field(
        default=None, foreign_key="icloudaccount.id"
    )
    icloud_account: Optional["ICloudAccount"] = Relationship(back_populates="user")
    # User 1:1* Google Account
    # TODO: Google account
    # google_account_id: Optional[int] = Field(
    #     default=None, foreign_key="googleaccount.id"
    # )
    # google_account: Optional["GoogleAccount"] = Relationship(back_populates="user")
    # User 1:1 business BankAccount
    bank_account_id: Optional[int] = Field(default=None, foreign_key="bankaccount.id")
    bank_account: Optional["BankAccount"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    # TODO: path to logo image
    logo: Optional[str]


class ICloudAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str
    user: User = OneToOneRelationship(back_populates="icloud_account")


class GoogleAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str
    # user: User = OneToOneRelationship(back_populates="google_account")


class Bank(SQLModel, table=True):
    """A bank."""

    id: Optional[int] = Field(default=None, primary_key=True)
    BLZ: str  # TODO: add type / validator


class BankAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    IBAN: str
    BIC: str
    # username: str  # online banking user name
    user: User = Relationship(back_populates="bank_account")


class Contact(SQLModel, table=True):
    """An entry in the address book."""

    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: Optional[str]
    last_name: Optional[str]
    company: Optional[str]
    email: Optional[str]
    address_id: Optional[int] = Field(default=None, foreign_key="address.id")
    address: Optional[Address] = Relationship(
        back_populates="contacts", sa_relationship_kwargs={"lazy": "subquery"}
    )
    invoicing_contact_of: List["Client"] = Relationship(
        back_populates="invoicing_contact", sa_relationship_kwargs={"lazy": "subquery"}
    )
    # post address

    @property
    def name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        elif self.company:
            return self.company
        else:
            return None

    def print_address(self, address_only: bool = False):
        """Print address in common format."""
        if self.address is None:
            return ""

        if address_only:
            return textwrap.dedent(
                f"""
                {self.address.street} {self.address.number}
                {self.address.postal_code} {self.address.city}
                {self.address.country}"""
            )

        return textwrap.dedent(
            f"""
        {self.name}
        {self.company}
        {self.address.street} {self.address.number}
        {self.address.postal_code} {self.address.city}
        {self.address.country}
        """
        )


class Client(SQLModel, table=True):
    """A client the freelancer has contracted with."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(default="")
    # Client 1:1 invoicing Contact
    invoicing_contact_id: int = Field(default=None, foreign_key="contact.id")
    invoicing_contact: Contact = Relationship(
        back_populates="invoicing_contact_of",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    contracts: List["Contract"] = Relationship(
        back_populates="client", sa_relationship_kwargs={"lazy": "subquery"}
    )
    # non-invoice related contact person?


class Contract(SQLModel, table=True):
    """A contract defines the business conditions of a project"""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="Short description of the contract.")
    client: Client = Relationship(
        back_populates="contracts", sa_relationship_kwargs={"lazy": "subquery"}
    )
    signature_date: datetime.date = Field(
        description="Date on which the contract was signed",
    )
    start_date: datetime.date = Field(
        description="Date from which the contract is valid",
    )
    end_date: Optional[datetime.date] = Field(
        description="Date until which the contract is valid",
    )
    # Contract n:1 Client
    client_id: Optional[int] = Field(
        default=None,
        foreign_key="client.id",
    )
    rate: condecimal(decimal_places=2) = Field(
        description="Rate of remuneration",
    )
    is_completed: bool = Field(
        default=False, description="flag marking if contract has been completed"
    )
    currency: str  # TODO: currency representation
    VAT_rate: Decimal = Field(
        description="VAT rate applied to the contractual rate.",
        default=0.19,  # TODO: configure by country?
    )
    unit: TimeUnit = Field(
        description="Unit of time tracked. The rate applies to this unit.",
        sa_column=sqlalchemy.Column(sqlalchemy.Enum(TimeUnit)),
        default=TimeUnit.hour,
    )
    units_per_workday: int = Field(
        description="How many units of time (e.g. hours) constitute a whole work day?",
        default=8,
    )
    volume: Optional[int] = Field(
        description="Number of units agreed on",
    )
    term_of_payment: Optional[int] = Field(
        description="How many days after receipt of invoice this invoice is due.",
        default=31,
    )
    billing_cycle: Cycle = Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Enum(Cycle)),
        description="How often is an invoice sent?",
    )
    projects: List["Project"] = Relationship(
        back_populates="contract", sa_relationship_kwargs={"lazy": "subquery"}
    )
    invoices: List["Invoice"] = Relationship(
        back_populates="contract", sa_relationship_kwargs={"lazy": "subquery"}
    )
    # TODO: model contractual promises like "at least 2 days per week"

    @property
    def volume_as_time(self):
        return self.volume * self.unit.to_timedelta()

    def is_active(self) -> bool:
        if self.end_date:
            today = datetime.date.today()
            return self.end_date > today
        else:
            return True

    def is_upcoming(self) -> bool:
        today = datetime.date.today()
        return self.start_date > today

    def get_status(self) -> str:
        if self.is_active():
            return "Active"
        elif self.is_upcoming():
            return "Upcoming"
        elif self.is_completed:
            return "Completed"
        else:
            # default
            return "All"


class Project(SQLModel, table=True):
    """A project is a group of contract work for a client."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(
        description="A short, unique title", sa_column_kwargs={"unique": True}
    )
    description: str = Field(
        description="A longer description of the project", default=""
    )
    # TODO: tag: constr(regex=r"#\S+")
    tag: str = Field(description="A unique tag", sa_column_kwargs={"unique": True})
    start_date: datetime.date
    end_date: datetime.date
    is_completed: bool = Field(
        default=False, description="marks if the project is completed"
    )
    # Project m:n Contract
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    contract: Contract = Relationship(
        back_populates="projects",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    # Project 1:n Timesheet
    timesheets: List["Timesheet"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    # Project 1:n Invoice
    invoices: List["Invoice"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"lazy": "subquery"},
    )

    @property
    def client(self):
        return self.contract.client

    def get_brief_description(self):
        if len(self.description) <= 108:
            return self.description
        else:
            return f"{self.description[0:108]}..."

    def is_active(self) -> bool:
        if self.end_date:
            today = datetime.date.today()
            return self.end_date >= today
        else:
            return True

    def is_upcoming(self) -> bool:
        today = datetime.date.today()
        return self.start_date > today

    def get_status(self) -> str:
        if self.is_active():
            return "Active"
        elif self.is_upcoming():
            return "Upcoming"
        elif self.is_completed:
            return "Completed"
        else:
            # default
            return "All"


class TimeTrackingItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # TimeTrackingItem n : 1 TimeSheet
    timesheet_id: Optional[int] = Field(default=None, foreign_key="timesheet.id")
    timesheet: Optional["Timesheet"] = Relationship(back_populates="items")
    #
    begin: datetime.datetime
    end: Optional[datetime.datetime]
    duration: datetime.timedelta
    title: str
    tag: str
    description: Optional[str]


class Timesheet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    date: datetime.date
    # period: str
    # table: pandas.DataFrame
    # TODO: store dataframe as dict
    # table: Dict = Field(default={}, sa_column=sqlalchemy.Column(sqlalchemy.JSON))
    # Timesheet n:1 Project
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    project: Project = Relationship(
        back_populates="timesheets",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    # invoice: "Invoice" = Relationship(back_populates="timesheet")
    # period: str
    comment: Optional[str]
    items: List[TimeTrackingItem] = Relationship(back_populates="timesheet")

    # class Config:
    #     arbitrary_types_allowed = True

    @property
    def total(self) -> datetime.timedelta:
        """Sum of time in timesheet."""
        total_time = self.table["duration"].sum()
        return total_time

    @property
    def table(self) -> pandas.DataFrame:
        """items as DataFrame"""
        return to_dataframe(self.items)

    @property
    def empty(self) -> bool:
        return len(self.items) == 0


class Invoice(SQLModel, table=True):
    """An invoice is a bill for a client."""

    id: Optional[int] = Field(default=None, primary_key=True)
    number: str
    # date and time
    date: datetime.date
    # due_date: datetime.date
    # sent_date: datetime.date
    # Invoice 1:n Timesheet ?
    # timesheet_id: Optional[int] = Field(default=None, foreign_key="timesheet.id")
    # timesheet: Timesheet = Relationship(back_populates="invoice")
    # Invoice n:1 Contract ?
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    contract: Contract = Relationship(
        back_populates="invoices",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    # Invoice n:1 Project
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    project: Project = Relationship(
        back_populates="invoices",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    # status -- corresponds to InvoiceStatus enum above
    sent: Optional[bool] = Field(default=False)
    paid: Optional[bool] = Field(default=False)
    cancelled: Optional[bool] = Field(default=False)
    # payment: Optional["Payment"] = Relationship(back_populates="invoice")
    # invoice items
    items: List["InvoiceItem"] = Relationship(
        back_populates="invoice",
        sa_relationship_kwargs={"lazy": "subquery"},
    )
    rendered: bool = Field(default=False)

    #
    @property
    def sum(self) -> Decimal:
        """Sum over all invoice items."""
        return sum([item.subtotal for item in self.items])

    @property
    def VAT_total(self) -> Decimal:
        """Sum of VAT over all invoice items."""
        return sum(item.VAT for item in self.items)

    @property
    def total(self) -> Decimal:
        """Total invoiced amount."""
        return self.sum + self.VAT_total

    def generate_number(self, pattern=None, counter=None):
        """Generate an invoice number"""
        date_prefix = self.date.strftime("%Y-%m-%d")
        # suffix = hashlib.shake_256(str(uuid.uuid4()).encode("utf-8")).hexdigest(2)
        # TODO: auto-increment suffix for invoices generated on the same day
        if counter is None:
            counter = 1
        suffix = f"{counter:02}"
        self.number = f"{date_prefix}-{suffix}"

    @property
    def due_date(self):
        """Date until which payment is due."""
        return self.date + datetime.timedelta(days=self.contract.term_of_payment)

    @property
    def client(self):
        return self.contract.client

    @property
    def prefix(self):
        """A string that can be used as the prefix of a file name, or a folder name."""
        client_suffix = self.client.name.lower().split()[0]
        prefix = f"{self.number}-{client_suffix}"
        return prefix

    @property
    def file_name(self):
        """A string that can be used as a file name."""
        return f"{self.prefix}.pdf"


class InvoiceItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # date and time
    start_date: datetime.date = Field(description="Start date of the invoice item.")
    end_date: Optional[datetime.date] = Field(
        description="End date of the invoice item."
    )
    #
    quantity: int
    unit: str
    unit_price: Decimal
    description: str
    VAT_rate: Decimal
    # invoice
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    invoice: Invoice = Relationship(
        back_populates="items",
        sa_relationship_kwargs={"lazy": "subquery"},
    )

    @property
    def subtotal(self) -> Decimal:
        """."""
        return self.quantity * self.unit_price

    @property
    def VAT(self) -> Decimal:
        """VAT for the invoice item."""
        return self.subtotal * self.VAT_rate


# class Payment(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     # invoice: Invoice = Relationship(back_populates="payment")


class TimelineItem(SQLModel, table=True):
    """An item that appears in the freelancer's timeline."""

    id: Optional[int] = Field(default=None, primary_key=True)
    time: datetime.datetime = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
        )
    )
    content: str


class Settings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
