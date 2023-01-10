import datetime

import faker

from core.models import Cycle, IntentResult, TimeUnit
from typing import Optional

from tuttle.model import (
    Client,
    Contract,
    Contact,
    Project,
)


class ProjectDataSource:
    def __init__(self):
        super().__init__()

    def get_all_projects_as_map(
        self,
    ) -> IntentResult:
        projects = self._get_dummy_projects()
        return IntentResult(was_intent_successful=True, data=projects)

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
        return IntentResult(was_intent_successful=True, data=project)

    def get_project_by_id(self, projectId) -> IntentResult:
        try:
            fake = faker.Faker()
            p = self._get_fake_project(fake, int(projectId))
            return IntentResult(was_intent_successful=True, data=p)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @Projects.data_source_impl.get_project_by_id {e}",
                data=None,
            )
