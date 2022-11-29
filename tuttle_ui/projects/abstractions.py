from abc import ABC, abstractmethod
from typing import List, Optional, Mapping

import datetime
from core.abstractions import ClientStorage
from core.models import IntentResult
from .project_model import Project
from clients.client_model import Client
from contracts.contract_model import Contract


class ProjectDataSource(ABC):
    """Defines methods for instantiating, viewing, updating, saving and deleting projects"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_all_projects_as_map(
        self,
    ) -> IntentResult:
        """if successful, returns projects as data mapped as projectId -> project"""
        pass

    @abstractmethod
    def save_project(
        self,
        id: int,
        contract_id: int,
        contract: Contract,
        title: str,
        description: str,
        unique_tag: str,
        start_date: datetime.date,
        end_date: datetime.date,
        is_completed: bool = False,
    ) -> IntentResult:
        """attempts to create or update a project

        if project is passed, then it is an update operation
        returns the new /updated project as data if successful
        """
        pass

    @abstractmethod
    def get_project_by_id(self, projectId) -> IntentResult:
        """if successful, returns the project as data"""
        pass


class ProjectsIntent(ABC):
    """Handles project view intents"""

    def __init__(self, data_source: ProjectDataSource, local_storage: ClientStorage):
        super().__init__()
        self.local_storage = local_storage
        self.data_source = data_source

    @abstractmethod
    def get_all_projects_as_map(
        self,
    ) -> Mapping[int, Project]:
        """if successful, returns projects as data mapped as projectId -> project"""
        pass

    @abstractmethod
    def save_project(
        self,
        id: str,
        title: str,
        description: str,
        unique_tag: str,
        start_date: datetime.date,
        end_date: datetime.date,
        is_completed: bool = False,
        contract: Optional[Contract] = None,
        project: Optional[Project] = None,
    ) -> IntentResult:
        """attempts to create or update a project

        if project is passed, then it is an update operation
        returns the new /updated project as data if successful
        """
        pass

    @abstractmethod
    def get_project_by_id(self, projectId) -> IntentResult:
        """if successful, returns the project as data"""
        pass

    @abstractmethod
    def get_all_clients_as_map(
        self,
    ) -> Mapping[int, Client]:
        """if successful, returns clients as data mapped as clientId -> client"""
        pass

    @abstractmethod
    def get_all_contracts_as_map(
        self,
    ) -> Mapping[int, Contract]:
        """if successful, returns contracts as data mapped as contractId -> contract"""
        pass

    @abstractmethod
    def get_completed_projects(self) -> Mapping[int, Project]:
        """filters projects to display only completed projects"""
        pass

    @abstractmethod
    def get_active_projects(self) -> Mapping[int, Project]:
        """filters projects to display only active projects"""
        pass

    @abstractmethod
    def get_upcoming_projects(self) -> Mapping[int, Project]:
        """filters projects to display only upcoming projects"""
        pass
