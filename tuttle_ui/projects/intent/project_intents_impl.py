from projects.abstractions.project_intents import ProjectsIntent
from core.abstractions.local_cache import LocalCache
from projects.model.projects_data_source_impl import ProjectDataSourceImpl
from projects.abstractions.project_intents_result import ProjectIntentsResult
from typing import Mapping
from projects.model.projects_model import Project
from authentication.utils.auth_data_keys import USER_ID


class ProjectIntentImpl(ProjectsIntent):
    def __init__(self, cache: LocalCache):
        super().__init__(cache=cache, dataSource=ProjectDataSourceImpl())

    def get_total_projects_count(self) -> int:
        result = self.dataSource.get_total_projects_count()
        if result.wasIntentSuccessful:
            return result.data
        else:
            # TODO log error
            return 0

    def get_all_projects(self) -> Mapping[str, Project]:
        result = self.dataSource.get_all_projects_as_map()
        if result.wasIntentSuccessful:
            return result.data
        else:
            # TODO log error
            return {}

    def cache_projects_data(self, key: str, data: any):
        self.cache.set_value(key, data)
