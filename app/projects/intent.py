from typing import List, Optional, Mapping
import datetime
from core.models import IntentResult
from .data_source import ProjectDataSource

from loguru import logger
from clients.intent import ClientsIntent
from contracts.intent import ContractsIntent

from tuttle.model import (
    Client,
    Project,
    Contract,
)


class ProjectsIntent:
    def __init__(
        self,
    ):
        self.data_source = ProjectDataSource()
        self.clients_intent = ClientsIntent()
        self.contracts_intent = ContractsIntent()

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
            result.error_msg = "Something went wrong, failed to load the project"
        return result

    def get_all_clients_as_map(self) -> Mapping[int, Client]:
        return self.clients_intent.get_all_clients_as_map()

    def get_all_contracts_as_map(self) -> Mapping[int, Contract]:
        return self.contracts_intent.get_all_contracts_as_map()

    def get_all_projects_as_map(self) -> Mapping[int, Project]:
        if not self.all_projects_cache:
            self._clear_cached_results()
            self.all_projects_cache = {}
            result = self.data_source.get_all_projects()
            if result.was_intent_successful:
                projects = result.data
                projects_map = {project.id: project for project in projects}
                self.all_projects_cache = projects_map
            else:
                logger.error(result.log_message)
        return self.all_projects_cache

    def get_completed_projects(self) -> Mapping[int, Project]:
        if not self.all_projects_cache:
            self.get_all_projects_as_map()
        if not self.completed_projects_cache:
            self.completed_projects_cache = {}
            for key in self.all_projects_cache:
                p: Project = self.all_projects_cache[key]
                if p.is_completed:
                    self.completed_projects_cache[key] = p
        return self.completed_projects_cache

    def get_active_projects(self) -> Mapping[int, Project]:
        if not self.all_projects_cache:
            self.get_all_projects_as_map()
        if not self.active_projects_cache:
            self.active_projects_cache = {}
            for key in self.all_projects_cache:
                p = self.all_projects_cache[key]
                if p.is_active():
                    self.active_projects_cache[key] = p
        return self.active_projects_cache

    def get_upcoming_projects(self) -> Mapping[int, Project]:
        if not self.all_projects_cache:
            self.get_all_projects_as_map()
        if not self.upcoming_projects_cache:
            self.upcoming_projects_cache = {}
            for key in self.all_projects_cache:
                p = self.all_projects_cache[key]
                if p.is_upcoming():
                    self.upcoming_projects_cache[key] = p
        return self.upcoming_projects_cache

    def delete_project_by_id(self, project_id: str):
        result: IntentResult = self.data_source.delete_project_by_id(project_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete that project! Please retry"
        else:
            # remove it from all caches
            if self.all_projects_cache and project_id in self.all_projects_cache:
                self.all_projects_cache[project_id]
            if (
                self.completed_projects_cache
                and project_id in self.completed_projects_cache
            ):
                self.completed_projects_cache[project_id]
            if self.active_projects_cache and project_id in self.active_projects_cache:
                self.active_projects_cache[project_id]
            if (
                self.upcoming_projects_cache
                and project_id in self.upcoming_projects_cache
            ):
                self.upcoming_projects_cache[project_id]
        return result
