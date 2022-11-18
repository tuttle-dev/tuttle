from projects.abstractions.project_intents import ProjectsIntent
from core.abstractions.local_cache import LocalCache
from projects.model.projects_model import ProjectModelImpl
from projects.abstractions.project_intents_result import ProjectIntentsResult

from authentication.utils.auth_data_keys import USER_ID


class ProjectIntentImpl(ProjectsIntent):
    def __init__(self, cache: LocalCache):
        super().__init__(cache=cache, model=ProjectModelImpl())

    def get_total_projects_count(self) -> int:
        result = self.model.get_total_projects_count()
        if result.wasIntentSuccessful:
            return result.data
        else:
            # TODO log error
            return 0

    def cache_projects_data(self, key: str, data: any):
        self.cache.set_value(key, data)
