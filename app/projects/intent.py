from typing import Mapping, Optional, Union

import datetime

from clients.intent import ClientsIntent
from contracts.intent import ContractsIntent
from core.intent_result import IntentResult

from tuttle.model import Client, Contract, Project

from .data_source import ProjectDataSource


class ProjectsIntent:
    """Handles intents related to the projects data Ui"""

    def __init__(
        self,
    ):
        self._data_source = ProjectDataSource()
        self._clients_intent = ClientsIntent()
        self._contracts_intent = ContractsIntent()

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
    ) -> IntentResult[Optional[Project]]:
        """Create a new project, or Update the project if a project is provided

        Args:
        title (str): Title of the project
        description (str): Description of the project
        unique_tag (str): Unique tag of the project
        start_date (datetime.date): Start date of the project
        end_date (datetime.date): End date of the project
        is_completed (bool): Whether the project is completed
        contract (Optional[Contract]): Contract to which the project belongs
        project (Optional[Project]): Project to be updated

        Returns:
        IntentResult:
            was_intent_successful : bool
            data :  Project if was_intent_successful else None
            log_message  : str  if an error or exception occurs
            exception : Exception if an exception occurs
        """
        if not project:
            # create a project, this is not an update
            project = Project()

        project.title = title
        project.description = description
        project.tag = unique_tag
        project.start_date = start_date
        project.end_date = end_date
        project.is_completed = is_completed
        project.contract = contract
        result: IntentResult = self._data_source.save_project(
            project=project,
        )
        if not result.was_intent_successful:
            result.error_msg = "Failed to save the project. Please retry"
            result.log_message_if_any()
        return result

    def get_project_by_id(self, projectId) -> IntentResult[Optional[Project]]:
        """
        Get the project by id

        Args:
        project_id (int): ID of the project

        Returns:
        IntentResult:
            was_intent_successful : bool
            data :  Project if was_intent_successful else None
            log_message  : str  if an error or exception occurs
            exception : Exception if an exception occurs
        """
        result: IntentResult = self._data_source.get_project_by_id(projectId=projectId)
        if not result.was_intent_successful:
            result.error_msg = "Something went wrong, failed to load the project"
            result.log_message_if_any()
        return result

    def get_all_clients_as_map_intent(self) -> Mapping[int, Client]:
        """Get all clients as a map of client_id to client object"""
        return self._clients_intent.get_all_clients_as_map()

    def get_all_contracts_as_map_intent(self) -> Mapping[int, Contract]:
        """Get all contracts as a map of contract_id to contract object"""
        return self._contracts_intent.get_all_contracts_as_map()

    def get_all_projects_as_map(self) -> Mapping[int, Project]:
        """Get all projects as a map of project_id to project object"""
        result: IntentResult = self._data_source.get_all_projects()
        if result.was_intent_successful:
            projects = result.data
            projects_map = {project.id: project for project in projects}
            return projects_map
        else:
            result.log_message_if_any()
            return {}

    def get_completed_projects_as_map(self) -> Mapping[int, Project]:
        """Get all completed projects as a map of project_id to project object"""
        _all_projects = self.get_all_projects_as_map()
        _completed_projects = {}
        for key in _all_projects:
            p: Project = _all_projects[key]
            if p.is_completed:
                _completed_projects[key] = p
        return _completed_projects

    def get_active_projects_as_map(
        self,
    ) -> Mapping[int, Project]:
        """Get all active projects as a map of project_id to project object"""
        _all_projects = self.get_all_projects_as_map()
        _active_projects = {}
        for key in _all_projects:
            p: Project = _all_projects[key]
            if p.is_active():
                _active_projects[key] = p
        return _active_projects

    def get_upcoming_projects_as_map(self) -> Mapping[int, Project]:
        """Get all upcoming projects as a map of project_id to project object"""
        _all_projects = self.get_all_projects_as_map()
        _upcoming_projects = {}
        for key in _all_projects:
            p: Project = _all_projects[key]
            if p.is_upcoming():
                _upcoming_projects[key] = p
        return _upcoming_projects

    def delete_project_by_id(self, project_id: str) -> IntentResult[None]:
        """
        Delete the project by id

        Args:
        project_id (int): ID of the project to be deleted

        Returns:
        IntentResult:
            was_intent_successful : bool
            data : None
            log_message  : str  if an error or exception occurs
            exception : Exception if an exception occurs
        """
        result: IntentResult = self._data_source.delete_project_by_id(project_id)
        if not result.was_intent_successful:
            result.error_msg = "Failed to delete that project! Please retry"
            result.log_message_if_any()
        return result

    def toggle_project_completed_status(
        self, project: Project
    ) -> IntentResult[Project]:
        """Updates the project completed status"""
        project.is_completed = not project.is_completed
        result: IntentResult = self._data_source.save_project(project)
        if not result.was_intent_successful:
            # undo status toggle
            project.is_completed = not project.is_completed
            result.error_msg = "Failed to update the project's completed status"
            result.log_message_if_any()
        result.data = project
        return result
