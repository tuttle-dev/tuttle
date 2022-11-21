import typing
from abc import abstractmethod
from typing import Callable, Mapping

from flet import UserControl

from core.abstractions import DataSource
from core.abstractions import TuttleDestinationView
from core.abstractions import Intent
from core.abstractions import IntentResult
from core.abstractions import LocalCache
from projects.projects_model import Project


class ProjectIntentsResult(IntentResult):
    """Wrapper for results of executed project intents"""

    def __init__(
        self,
        data=None,
        wasIntentSuccessful: bool = False,
        errorMsgIfAny: str = "",
        logMsg: str = "",
    ):
        super().__init__(
            data=data,
            wasIntentSuccessful=wasIntentSuccessful,
            errorMsgIfAny=errorMsgIfAny,
            logMsg=logMsg,
        )


class ProjectDataSource(DataSource):
    """Defines methods for instantiating, viewing, updating, saving and deleting projects"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_total_projects_count() -> ProjectIntentsResult:
        """if successful, returns data as number of projects created so far"""
        pass

    @abstractmethod
    def get_all_projects_as_map(
        self,
    ) -> ProjectIntentsResult:
        """if successful, returns data as all projects this user has in a map"""
        pass


class ProjectsIntent(Intent):
    """Handles project view intents"""

    def __init__(self, dataSource: ProjectDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def get_total_projects_count(
        self,
    ) -> int:
        """returns the number of projects this user has"""
        pass

    @abstractmethod
    def get_all_projects(
        self,
    ) -> Mapping[str, Project]:
        """fetches all projects this user has"""
        pass

    @abstractmethod
    def get_completed_projects(self) -> Mapping[str, Project]:
        """filters projects to display only completed projects"""
        pass

    @abstractmethod
    def get_active_projects(self) -> Mapping[str, Project]:
        """filters projects to display only active projects"""
        pass

    @abstractmethod
    def get_upcoming_projects(self) -> Mapping[str, Project]:
        """filters projects to display only upcoming projects"""
        pass

    @abstractmethod
    def cache_projects_data(self, key: str, data: any):
        """caches frequently used key-value pairs related to projects"""
        pass


class ProjectDestinationView(TuttleDestinationView, UserControl):
    """Describes the destination screen that displays all projects

    initializes the intent handler
    """

    def __init__(
        self,
        intentHandler: ProjectsIntent,
        onChangeRouteCallback: Callable[[str, typing.Optional[any]], None],
    ):
        super().__init__(
            intentHandler=intentHandler, onChangeRouteCallback=onChangeRouteCallback
        )
        self.intentHandler = intentHandler
