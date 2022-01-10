"""Online banking functionality."""

import getpass
from fints.client import FinTS3PinTanClient
from loguru import logger

from .model import BankAccount, Bank


class Banking:
    """."""

    def __init__(self, bank: Bank):
        self.bank = bank
        self.product_id = None  # TODO: register product ID before deployment

    def connect(self):
        """Connect to the online banking interface via FinTS."""
        self.client = FinTS3PinTanClient(
            self.bank.BLZ,  # Your bank's BLZ
            getpass.getpass("user name: "),  # Your login name
            getpass.getpass("PIN:"),  # Your banking PIN
            "https://hbci-pintan.gad.de/cgi-bin/hbciservlet",
            product_id=self.product_id,
        )

    def get_accounts(self):
        """List SEPA accounts."""
        with self.client as client:
            accounts = client.get_sepa_accounts()
            return accounts
