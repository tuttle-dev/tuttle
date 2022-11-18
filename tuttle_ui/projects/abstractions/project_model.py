from core.abstractions.model import Model
from abc import abstractmethod
from projects.abstractions.project_intents_result import ProjectIntentsResult


class ProjectModel(Model):
    """Defines methods for instantiating, viewing, updating, saving and deleting projects"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_total_projects_count() -> ProjectIntentsResult:
        """if successful, returns data as number of projects created so far"""
        pass
