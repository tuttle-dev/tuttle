import datetime
from typing import Mapping

from projects.abstractions import ProjectDataSource, ProjectIntentsResult

from .projects_model import Project


# TODO implement
class ProjectDataSourceImpl(ProjectDataSource):
    def __init__(self):
        super().__init__()
        self.projects: Mapping[str, Project] = {}

    def get_total_projects_count(self) -> ProjectIntentsResult:
        return ProjectIntentsResult(
            wasIntentSuccessful=True, data=self._get_total_projects()
        )

    def get_all_projects_as_map(self) -> ProjectIntentsResult:
        self._set_dummy_projects()
        return ProjectIntentsResult(wasIntentSuccessful=True, data=self.projects)

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _get_total_projects(self):
        return 50

    def _set_dummy_projects(self):
        self.projects.clear()
        total = self._get_total_projects()
        for i in range(total):
            p = Project(
                id=i,
                contract_id=i * 2,
                client_id=i * 3,
                title=f"Project {i}",
                description=f"Dummy project {i}",
                unique_tag=f"dummy{i}",
                is_completed=True if i % 2 == 0 else False,
                start_date=datetime.date.today(),
                end_date=datetime.date.today() + datetime.timedelta((i + 1)),
            )
            self.projects[p.id] = p
