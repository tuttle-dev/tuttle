from core.abstractions.data_source import DataSource
from abc import abstractmethod
from projects.abstractions.project_intents_result import ProjectIntentsResult


class ProjectDataSource(DataSource):
    """Defines methods for instantiating, viewing, updating, saving and deleting projects"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_total_projects_count() -> ProjectIntentsResult:
        """if successful, returns data as number of projects created so far"""
        pass

    @abstractmethod
    def get_all_projects_as_map(
        self,
    ) -> ProjectIntentsResult:
        """if successful, returns data as all projects this user has in a map"""
        pass
