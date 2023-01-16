from typing import Optional, Mapping
import datetime
from core.intent_result import IntentResult
from .data_source import ProjectDataSource

from clients.intent import ClientsIntent
from contracts.intent import ContractsIntent

from tuttle.model import (
    Client,
    Project,
    Contract,
)


class ProjectsIntent:
    """Handles Project C_R_U_D intents

    Intents handled (Methods)
    ---------------
    get_project_by_id_intent
        reading a project info given it's id

    get_all_clients_as_map_intent
        fetching existing clients as a map of client IDs to client

    get_all_contracts_as_map_intent
        fetching existing contracts as a map of contract IDs to contract

    get_upcoming_projects_as_map_intent
        fetching upcoming projects as a map of project IDs to project

    get_completed_projects_as_map_intent
        fetching completed projects as a map of project IDs to project

    get_active_projects_as_map_intent
        fetching active projects as a map of project IDs to project

    get_all_projects_as_map_intent
        fetching existing projects as a map of project IDs to project

    save_project_intent
        saving the project

    delete_project_by_id_intent
        deleting a project given it's id
    """

    def __init__(
        self,
    ):
        """
        Attributes
        ----------
        _data_source : ProjectDataSource
            reference to the project's data source
        _clients_intent :  ClientsIntent
            reference to the client's Intent handler for forwarding client related intents
        _contracts_intent  : ContractsIntent
            reference to the contract's Intent handler for forwarding contact related intents
        _all_projects_cache : Mapping[str, Contract]
            caches fetched projects to reduce unnecessary database calls
        _completed_projects_cache : Mapping[str, Contract]
            caches completed projects to reduce unnecessary database calls
        _active_projects_cache  :   Mapping[str, Contract]
            caches active projects to reduce unnecessary database calls
        _upcoming_projects_cache : Mapping[str, Contract]
            caches upcoming projects to reduce unnecessary database calls
        """
        self._data_source = ProjectDataSource()
        self._clients_intent = ClientsIntent()
        self._contracts_intent = ContractsIntent()
        self._all_projects_cache: Mapping[int, Project] = None
        self._completed_projects_cache: Mapping[int, Project] = None
        self._active_projects_cache: Mapping[int, Project] = None
        self._upcoming_projects_cache: Mapping[int, Project] = None

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
        result = self._data_source.save_project(
            title=title,
            description=description,
            unique_tag=unique_tag,
            start_date=start_date,
            end_date=end_date,
            is_completed=is_completed,
            contract=contract,
            project=project,
        )
        if not result.was_intent_successful:
            result.error_msg = "Failed to save the project. Please retry"
            result.log_message_if_any()
        return result

    def get_project_by_id(self, projectId) -> IntentResult:
        result = self._data_source.get_project_by_id(projectId=projectId)
        if not result.was_intent_successful:
            result.error_msg = "Something went wrong, failed to load the project"
            result.log_message_if_any()
        return result

    def get_all_clients_as_map_intent(self) -> Mapping[int, Client]:
        return self._clients_intent.get_all_clients_as_map()

    def get_all_contracts_as_map_intent(self) -> Mapping[int, Contract]:
        return self._contracts_intent.get_all_contracts_as_map(reload_cache=True)

    def get_all_projects_as_map(
        self, reload_cache: bool = False
    ) -> Mapping[int, Project]:
        if reload_cache or not self._all_projects_cache:
            self._clear_cached_results()
            self._all_projects_cache = {}
            result = self._data_source.get_all_projects()
            if result.was_intent_successful:
                projects = result.data
                projects_map = {project.id: project for project in projects}
                self._all_projects_cache = projects_map
            else:
                result.log_message_if_any()
        return self._all_projects_cache

    def get_completed_projects_as_map(self) -> Mapping[int, Project]:
        if not self._all_projects_cache:
            self.get_all_projects_as_map()
        if not self._completed_projects_cache:
            self._completed_projects_cache = {}
            for key in self._all_projects_cache:
                p: Project = self._all_projects_cache[key]
                if p.is_completed:
                    self._completed_projects_cache[key] = p
        return self._completed_projects_cache

    def get_active_projects_as_map(self) -> Mapping[int, Project]:
        if not self._all_projects_cache:
            self.get_all_projects_as_map()
        if not self._active_projects_cache:
            self._active_projects_cache = {}
            for key in self._all_projects_cache:
                p = self._all_projects_cache[key]
                if p.is_active():
                    self._active_projects_cache[key] = p
        return self._active_projects_cache

    def get_upcoming_projects_as_map(self) -> Mapping[int, Project]:
        if not self._all_projects_cache:
            self.get_all_projects_as_map()
        if not self._upcoming_projects_cache:
            self._upcoming_projects_cache = {}
            for key in self._all_projects_cache:
                p = self._all_projects_cache[key]
                if p.is_upcoming():
                    self._upcoming_projects_cache[key] = p
        return self._upcoming_projects_cache

    def delete_project_by_id(self, project_id: str):
        result: IntentResult = self._data_source.delete_project_by_id(project_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete that project! Please retry"
            result.log_message_if_any()
        else:
            self._remove_project_from_caches(project_id)
        return result

    def _remove_project_from_caches(self, project_id):
        if self._all_projects_cache and project_id in self._all_projects_cache:
            del self._all_projects_cache[project_id]
        if (
            self._completed_projects_cache
            and project_id in self._completed_projects_cache
        ):
            del self._completed_projects_cache[project_id]
        if self._active_projects_cache and project_id in self._active_projects_cache:
            del self._active_projects_cache[project_id]
        if (
            self._upcoming_projects_cache
            and project_id in self._upcoming_projects_cache
        ):
            del self._upcoming_projects_cache[project_id]

    def _clear_cached_results(self):
        self._all_projects_cache = None
        self._completed_projects_cache = None
        self._active_projects_cache = None
        self._upcoming_projects_cache = None
