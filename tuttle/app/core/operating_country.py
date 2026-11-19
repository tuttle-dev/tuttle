from ...model import User


class OperatingCountryMixin:
    """For intents whose figures depend on the country the user operates in.

    Goes with ``SQLModelDataSourceMixin``, which provides ``query``.
    """

    def _get_country(self) -> str:
        """Determine the user's operating country for tax purposes."""
        try:
            users = self.query(User)
            if users and users[0].operating_country:
                return users[0].operating_country
        except Exception:
            pass
        return ""
