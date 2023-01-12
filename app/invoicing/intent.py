"""  """
from loguru import logger

from core.abstractions import IntentResult

from .data_source import InvoicingDataSource
from tuttle.model import Invoice
from projects.intent import ProjectsIntent


class InvoicingIntent:
    def __init__(self):
        self.projects_intent = ProjectsIntent()
        self.data_source = InvoicingDataSource()

    def get_all_projects_as_map(self) -> IntentResult:
        """if successful returns a map of active projects as data"""
        return self.projects_intent.get_active_projects()

    def get_invoices_for_project_as_map(self, project_id) -> IntentResult:
        """returns data as a map of invoices associated with a given project
        or an empty map if none exists"""
        result = self.data_source.get_invoices_for_project(project_id)
        if result.was_intent_successful:
            if not result.data:
                result.data = {}  # the Ui expects an empty map
                return result
            else:
                invoices_list = result.data
                result.data = {invoice.id: invoice for invoice in invoices_list}
                return result
        else:
            result.error_msg = "Failed to load invoices."
            return result

    def get_all_invoices(self) -> IntentResult:
        """returns data as a map of all invoices in the database"""
        result = self.data_source.get_all_invoices()
        if result.was_intent_successful:
            invoices = result.data
            invoices_map = {invoice.id: invoice for invoice in invoices}
            return IntentResult(
                data=invoices_map,
                was_intent_successful=True,
            )
        else:
            logger.error(result.log_message)
            logger.exception(result.exception)
            return IntentResult(
                was_intent_successful=False,
                error_msg="Failed to load invoices.",
            )
