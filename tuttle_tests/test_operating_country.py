"""The operating country is looked up in one place for the dashboard, tax and salary views."""

from types import SimpleNamespace

import pytest

from tuttle.app.core.operating_country import OperatingCountryMixin
from tuttle.app.dashboard.intent import DashboardIntent
from tuttle.app.salary.intent import SalaryIntent
from tuttle.app.tax.intent import TaxIntent
from tuttle.model import User


class Source(OperatingCountryMixin):
    def __init__(self, users):
        self.users = users

    def query(self, entity_type):
        assert entity_type is User
        if isinstance(self.users, Exception):
            raise self.users
        return self.users


def test_the_country_is_the_users_operating_country():
    assert Source([SimpleNamespace(operating_country="Germany")])._get_country() == "Germany"


@pytest.mark.parametrize(
    "users",
    [
        [],
        [SimpleNamespace(operating_country="")],
        RuntimeError("the database cannot be read"),
    ],
    ids=["no user", "no country set", "query fails"],
)
def test_no_country_is_an_empty_string(users):
    assert Source(users)._get_country() == ""


@pytest.mark.parametrize("intent", [DashboardIntent, TaxIntent, SalaryIntent])
def test_the_views_share_the_one_lookup(intent):
    assert intent._get_country is OperatingCountryMixin._get_country
