from core.abstractions.intent import Intent
from abc import abstractmethod
from projects.abstractions.project_model import ProjectModel
from core.abstractions.local_cache import LocalCache


class ProjectsIntent(Intent):
    """Handles project view intents"""

    def __init__(self, model: ProjectModel, cache: LocalCache):
        super().__init__(cache=cache, model=model)
        self.cache = cache
        self.model = model

    @abstractmethod
    def get_total_projects_count(
        self,
    ) -> int:
        """returns the number of projects this user has"""
        pass

    @abstractmethod
    def cache_projects_data(self, key: str, data: any):
        """caches frequently used key-value pairs related to projects"""
        pass
