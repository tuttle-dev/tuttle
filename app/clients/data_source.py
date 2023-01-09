from typing import Optional
import faker
from core.models import IntentResult
from .model import Client
from contacts.model import Contact

from tuttle.model import (
    Address,
)


class ClientDataSource:
    def __init__(self):
        self.clients = {}

    def get_client_by_id(self, clientId) -> IntentResult:
        fake = faker.Faker(
            ["fr_FR", "en_US", "de_DE", "es_ES", "it_IT", "sv_SE", "zh_CN"]
        )
        c = self._get_fake_client(fake, clientId)
        return IntentResult(was_intent_successful=True, data=c)

    def get_all_clients_as_map(self) -> IntentResult:
        self._set_dummy_clients()
        return IntentResult(was_intent_successful=True, data=self.clients)

    def save_client(self, client: Client) -> IntentResult:
        if client.id is None:
            # new client is being saved
            client.id = 1
            if client.invoicing_contact_id is None:
                # new contact is being saved
                client.invoicing_contact_id = 1
                client.invoicing_contact.id = 1
        return IntentResult(was_intent_successful=True, data=client)

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _set_dummy_clients(self):
        fake = faker.Faker(
            ["fr_FR", "en_US", "de_DE", "es_ES", "it_IT", "sv_SE", "zh_CN"]
        )

        self.clients.clear()
        total = 20
        for i in range(total):
            c = self._get_fake_client(fake, i)
            self.clients[c.id] = c

    def _get_fake_client(self, fake, id):
        invoicing_contact_id = int(id * 2)
        c = self._get_fake_contact(fake, invoicing_contact_id)

        return Client(
            id=id,
            title=fake.company(),
            invoicing_contact_id=invoicing_contact_id,
            invoicing_contact=c,
        )

    def _get_fake_contact(self, fake, id: int):
        try:
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
            c = Contact(
                id=id,
                first_name=first_name,
                last_name=last_name,
                email=fake.email(),
                company=fake.company(),
                address_id=a.id,
                address=a,
            )
            return c
        except Exception as e:
            return None
