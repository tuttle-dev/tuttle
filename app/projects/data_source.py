import datetime

from core.models import Cycle, IntentResult, TimeUnit
from typing import Optional
from core.abstractions import SQLModelDataSourceMixin
from tuttle.model import (
    Contract,
    Project,
)


class ProjectDataSource(SQLModelDataSourceMixin):
    def __init__(self):
        super().__init__()

    def get_all_projects_as_map(
        self,
    ) -> IntentResult:
        projects = self.query(Project)
        result = {project.id: project for project in projects}
        return IntentResult(was_intent_successful=True, data=result)

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
    ) -> IntentResult:
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
                log_message=f"Saving project failed with exception {e}",
            )

    def get_project_by_id(self, projectId) -> IntentResult:
        try:
            project = self.query_by_id(Project, projectId)
            return IntentResult(was_intent_successful=True, data=project)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @Projects.data_source_impl.get_project_by_id {e}",
                data=None,
            )
