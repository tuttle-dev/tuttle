from ...model import User
from ..core.abstractions import SQLModelDataSourceMixin


class UserDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the User model in the database"""

    def __init__(self):
        super().__init__()

    def get_user(self) -> User:
        """Get a user from the database

        Returns:
            User: The user
        """
        return self.query_the_only(User)
