from typing import List, Optional, Mapping
import datetime
from core.abstractions import ClientStorage
from core.models import IntentResult
from .project_model import Project
from clients.client_model import Client
from contracts.contract_model import Contract
from .data_source_impl import ProjectDataSourceImpl
from .abstractions import ProjectsIntent

from clients.data_source_impl import ClientDataSourceImpl
from contracts.data_source_impl import ContractDataSourceImpl


class ProjectsIntentImpl(ProjectsIntent):
    def __init__(self, local_storage: ClientStorage):
        super().__init__(ProjectDataSourceImpl(), local_storage)
        self.clients_data_source = ClientDataSourceImpl()
        self.contracts_data_source = ContractDataSourceImpl()

        self.all_projects_cache: Mapping[int, Project] = None
        self.completed_projects_cache: Mapping[int, Project] = None
        self.active_projects_cache: Mapping[int, Project] = None
        self.upcoming_projects_cache: Mapping[int, Project] = None

    def _clear_cached_results(self):
        self.all_projects_cache = None
        self.completed_projects_cache = None
        self.active_projects_cache = None
        self.upcoming_projects_cache = None

    def save_project(
        self,
        title: str,
        description: str,
        unique_tag: str,
        start_date: datetime.date,
        end_date: datetime.date,
        is_completed: bool = False,
        contract: Optional[Contract] = None,
        project: Optional[Project] = None,
    ) -> IntentResult:
        return self.data_source.save_project(
            title=title,
            description=description,
            unique_tag=unique_tag,
            start_date=start_date,
            end_date=end_date,
            is_completed=is_completed,
            contract=contract,
            project=project,
        )

    def get_project_by_id(self, projectId) -> IntentResult:
        result = self.data_source.get_project_by_id(projectId=projectId)
        if not result.was_intent_successful:
            result.error_msg = "-TODO- error message"
        return result

    def get_all_clients_as_map(self) -> Mapping[int, Client]:
        result = self.clients_data_source.get_all_clients_as_map()
        if result.was_intent_successful:
            return result.data
        else:
            return {}

    def get_all_contracts_as_map(self) -> Mapping[int, Contract]:
        result = self.contracts_data_source.get_all_contracts_as_map()
        if result.was_intent_successful:
            return result.data
        else:
            return {}

    def get_all_projects_as_map(self) -> Mapping[int, Project]:
        if not self.all_projects_cache:
            self._clear_cached_results()
            self.all_projects_cache = {}
            result = self.data_source.get_all_projects_as_map()
            if result.was_intent_successful:
                self.all_projects_cache = result.data
        return self.all_projects_cache

    def get_completed_projects(self) -> Mapping[int, Project]:
        if not self.completed_projects_cache:
            self.completed_projects_cache = {}
            for key in self.all_projects_cache:
                p = self.all_projects_cache[key]
                if p.is_completed:
                    self.completed_projects_cache[key] = p
        return self.completed_projects_cache

    def get_active_projects(self) -> Mapping[int, Project]:
        if not self.active_projects_cache:
            self.active_projects_cache = {}
            for key in self.all_projects_cache:
                p = self.all_projects_cache[key]
                if p.is_active():
                    self.active_projects_cache[key] = p
        return self.active_projects_cache

    def get_upcoming_projects(self) -> Mapping[int, Project]:
        if not self.upcoming_projects_cache:
            self.upcoming_projects_cache = {}
            for key in self.all_projects_cache:
                p = self.all_projects_cache[key]
                if p.is_upcoming():
                    self.upcoming_projects_cache[key] = p
        return self.upcoming_projects_cache
