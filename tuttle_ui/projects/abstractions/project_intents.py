from core.abstractions.intent import Intent
from abc import abstractmethod
from projects.abstractions.project_data_source import ProjectDataSource
from core.abstractions.local_cache import LocalCache
from typing import Mapping
from projects.model.projects_model import Project


class ProjectsIntent(Intent):
    """Handles project view intents"""

    def __init__(self, dataSource: ProjectDataSource, cache: LocalCache):
        super().__init__(cache=cache, dataSource=dataSource)
        self.cache = cache
        self.dataSource = dataSource

    @abstractmethod
    def get_total_projects_count(
        self,
    ) -> int:
        """returns the number of projects this user has"""
        pass

    @abstractmethod
    def get_all_projects(
        self,
    ) -> Mapping[str, Project]:
        """fetches all projects this user has"""
        pass

    @abstractmethod
    def get_completed_projects(self) -> Mapping[str, Project]:
        """filters projects to display only completed projects"""
        pass

    @abstractmethod
    def get_active_projects(self) -> Mapping[str, Project]:
        """filters projects to display only active projects"""
        pass

    @abstractmethod
    def get_upcoming_projects(self) -> Mapping[str, Project]:
        """filters projects to display only upcoming projects"""
        pass

    @abstractmethod
    def cache_projects_data(self, key: str, data: any):
        """caches frequently used key-value pairs related to projects"""
        pass
