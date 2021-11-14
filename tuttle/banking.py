"""Online banking functionality."""

import getpass
from fints.client import FinTS3PinTanClient
from loguru import logger


from model import BankAccount


class Banking:
    def __init__(
        self,
        account: BankAccount,
    ):
        self.account = account
        self.product_id = None  # TODO: register product ID before deployment

    def connect(self):
        """Connect to the online banking interface via FinTS."""
        self.connection = FinTS3PinTanClient(
            self.account.blz,  # Your bank's BLZ
            "myusername",  # Your login name
            getpass.getpass("PIN:"),  # Your banking PIN
            "https://hbci-pintan.gad.de/cgi-bin/hbciservlet",
            product_id=self.product_id,
        )
