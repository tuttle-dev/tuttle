from tuttle.model import (
    Contact,
    Address,
)

demo_contact = Contact(
    name="Sam Lowry",
    email="info@centralservices.com",
    address=Address(
        street="Main Street",
        number="9999",
        postal_code="55555",
        city="Sao Paolo",
        country="Brazil",
    ),
)

another_demo_contact = Contact(
    name="Harry Tuttle",
    company="Harry Tuttle - Heating Engineer",
    email="harry@tuttle.com",
    address=None,
)
