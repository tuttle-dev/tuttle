"""  """

from core.abstractions import IntentResult

from .data_source import InvoicingDataSource

from projects.data_source import ProjectDataSource


class InvoicingIntent:
    def __init__(self):
        self.project_data_source = ProjectDataSource()

    def get_all_projects_as_map(self) -> IntentResult:
        """returns a list of active projects"""
        # FIXME: why a method that does nothing but deletage to another method?
        result = self.project_data_source.get_all_projects_as_map()
        return IntentResult(was_intent_successful=True, data=[])
