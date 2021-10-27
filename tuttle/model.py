"""Object model."""

from typing import Optional

from sqlmodel import Field, SQLModel
from pydantic import EmailStr


class User(SQLModel):
    name: str

class Account(SQLModel):
    name: str
    number: str
    owner: User

class Contact(SQLModel):
    """An entry in the address book."""
    name: str
    e_mail: Optional[EmailStr]


class Client(Contact):
    pass

class Project(SQLModel):
    client: Client

class Contract(SQLModel):
    client: Client


class Timesheet(SQLModel):
    pass

class Invoice(SQLModel):
    contract: Contract
    timesheet: Timesheet


class Payment(SQLModel):
    invoice: Invoice