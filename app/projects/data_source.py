from typing import List, Optional, Union

import datetime

from core.abstractions import SQLModelDataSourceMixin
from core.intent_result import IntentResult

from tuttle.model import Contract, Project


class ProjectDataSource(SQLModelDataSourceMixin):
    """Handles manipulation of the Contract model in the database"""

    def __init__(self):
        super().__init__()

    def get_all_projects(
        self,
    ) -> IntentResult[List[Project]]:
        """Fetches all existing projects from the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  list[Project] if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            projects = self.query(Project)
            return IntentResult(was_intent_successful=True, data=projects)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @ProjectDataSource.get_all_projects {e.__class__.__name__}",
                exception=e,
            )

    def save_project(
        self,
        contract: Contract,
        title: str,
        description: str,
        unique_tag: str,
        start_date: datetime.date,
        end_date: datetime.date,
        is_completed: bool = False,
        project: Optional[Project] = None,
    ) -> IntentResult[Union[Project, None]]:
        """If project is provided,
        update the project with given info,
        else create a new project
        and store in the database

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  Project if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
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
            self.store(project)
            return IntentResult(was_intent_successful=True, data=project)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                data=None,
                log_message=f"Saving project failed with exception {e.__class__.__name__}",
                exception=e,
            )

    def get_project_by_id(self, projectId) -> IntentResult[Union[Project, None]]:
        """Fetches the project from the database with the given id

        Returns:
            IntentResult:
                was_intent_successful : bool
                data :  Project if was_intent_successful else None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            project = self.query_by_id(Project, projectId)
            return IntentResult(was_intent_successful=True, data=project)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @Projects.get_project_by_id {e.__class__.__name__}",
                data=None,
            )

    def delete_project_by_id(self, project_id) -> IntentResult:
        """Deletes the project with the corresponding id

        Returns:
            IntentResult:
                was_intent_successful : bool
                data : None
                log_message  : str  if an error or exception occurs
                exception : Exception if an exception occurs
        """
        try:
            self.delete_by_id(Project, project_id)
            return IntentResult(was_intent_successful=True)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @Projects.delete_project_by_id {e.__class__.__name__}",
                exception=e,
            )
