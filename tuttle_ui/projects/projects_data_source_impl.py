import datetime
from typing import Mapping

from projects.abstractions import ProjectDataSource
from projects.utils import ProjectIntentsResult

from .projects_model import Project
from clients.client_model import Client
from contracts.contract_model import Contract

# TODO implement
class ProjectDataSourceImpl(ProjectDataSource):
    def __init__(self):
        super().__init__()
        self.projects: Mapping[str, Project] = {}
        self.clients: Mapping[str, Client] = {}
        self.contracts: Mapping[str, Contract] = {}

    def get_total_projects_count(self) -> ProjectIntentsResult:
        return ProjectIntentsResult(
            wasIntentSuccessful=True, data=self._get_total_projects()
        )

    def get_all_projects_as_map(self) -> ProjectIntentsResult:
        self._set_dummy_projects()
        return ProjectIntentsResult(wasIntentSuccessful=True, data=self.projects)

    def get_all_clients_as_map(self):
        return self.clients

    def get_all_contracts_as_map(self):
        return self.contracts

    def create_client(self, title: str) -> ProjectIntentsResult:
        client = Client(id=1, title=title)
        self.clients[str(client.id)] = client
        return ProjectIntentsResult(wasIntentSuccessful=True, data=client.id)

    def create_contract(self, description: str) -> ProjectIntentsResult:
        contract = Contract(id=1, description=description)
        self.contracts[str(contract.id)] = contract
        return ProjectIntentsResult(wasIntentSuccessful=True, data=contract.id)

    def save_project(
        self,
        title: str,
        description: str,
        startDate: datetime.date,
        endDate: datetime.date,
        tag: str,
        clientId: str,
        contractId: str,
    ) -> ProjectIntentsResult:
        return ProjectIntentsResult(wasIntentSuccessful=False)

    def get_project_by_id(self, projectId):
        i = int(projectId)
        self.projects[projectId] = Project(
            id=i,
            contract_id=i * 2,
            client_id=i * 3,
            title=f"Project {i}",
            description=f"Dummy project {i} Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
            unique_tag=f"dummy{i}",
            is_completed=True if i % 2 == 0 else False,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta((i + 1)),
        )
        if projectId in self.projects:
            return self.projects[projectId]
        else:
            return None

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
