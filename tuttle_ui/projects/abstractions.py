import typing
from abc import abstractmethod
from typing import Callable, Mapping, Optional

from flet import UserControl
import datetime
from core.abstractions import DataSource
from core.abstractions import TuttleDestinationView
from core.abstractions import Intent
from core.abstractions import LocalCache
from projects.projects_model import Project
from projects.utils import ProjectIntentsResult
from clients.client_model import Client
from contracts.contract_model import Contract


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

    @abstractmethod
    def create_contract(self, description: str) -> ProjectIntentsResult:
        """attempts to create a new contract

        returns new contract id as data if successful
        """
        pass

    @abstractmethod
    def create_client(self, title: str) -> ProjectIntentsResult:
        """attempts to create a new client

        returns new client id as data if successful
        """
        pass

    @abstractmethod
    def get_all_clients_as_map(
        self,
    ) -> Mapping[str, Client]:
        """Returns all existing clients, mapped as id:str to object:Client"""
        pass

    @abstractmethod
    def get_all_contracts_as_map(
        self,
    ) -> Mapping[str, Contract]:
        """Returns all existing contracts, mapped as id:str to object:Contract"""
        pass

    @abstractmethod
    def save_project(
        self,
        title: str,
        description: str,
        startDate: datetime.date,
        endDate: datetime.date,
        tag: str,
        clientId: str,
        contractId: str,
    ) -> ProjectIntentsResult:
        """attempts to save a project

        returns new project id as data if successful
        """
        pass

    @abstractmethod
    def get_project_by_id(self, projectId) -> Optional[Project]:
        """if successful, returns the project as data"""
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

    @abstractmethod
    def create_contract(self, description: str) -> ProjectIntentsResult:
        """attempts to create a new contract

        returns new contract id as data if intent is successful
        """
        pass

    @abstractmethod
    def create_client(self, title: str) -> ProjectIntentsResult:
        """attempts to create a new client

        returns new client id as data if intent is successful
        """
        pass

    @abstractmethod
    def get_all_clients_as_map(
        self,
    ) -> Mapping[str, str]:
        """Returns all existing clients, mapped as id to title"""
        pass

    @abstractmethod
    def get_all_contracts_as_map(
        self,
    ) -> Mapping[str, str]:
        """Returns all existing contracts, mapped as id to description"""
        pass

    @abstractmethod
    def save_project(
        self,
        title: str,
        description: str,
        start_date: datetime.date,
        end_date: datetime.date,
        tag: str,
        client_id: str,
        contract_id: str,
    ) -> ProjectIntentsResult:
        """attempts to save a project

        returns new project id as data if successful
        """
        pass

    @abstractmethod
    def get_project_by_id(self, projectId) -> ProjectIntentsResult:
        """if successful, returns the project as data"""
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
