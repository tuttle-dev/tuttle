from typing import Mapping

from user.auth_data_keys import USER_ID
from core.abstractions import LocalCache
from projects.abstractions import ProjectsIntent
from projects.utils import ProjectIntentsResult
from projects.projects_data_source_impl import ProjectDataSourceImpl
from projects.projects_model import Project
from res.strings import (
    CREATE_CLIENT_FAILED_ERR,
    CREATE_CONTRACT_FAILED_ERR,
    CREATE_PROJECT_FAILED,
    PROJECT_NOT_FOUND,
)
import datetime


class ProjectIntentImpl(ProjectsIntent):
    def __init__(self, cache: LocalCache):
        super().__init__(cache=cache, dataSource=ProjectDataSourceImpl())
        self.allProjectsCache: Mapping[str, Project] = None
        self.completedProjectsCache: Mapping[str, Project] = None
        self.activeProjectsCache: Mapping[str, Project] = None
        self.upcomingProjectsCache: Mapping[str, Project] = None

    def get_total_projects_count(self) -> int:
        result = self.dataSource.get_total_projects_count()
        if result.wasIntentSuccessful:
            return result.data
        else:
            # TODO log error
            return 0

    def get_completed_projects(self):
        if not self.completedProjectsCache:
            self.completedProjectsCache = {}
            for key in self.allProjectsCache:
                p = self.allProjectsCache[key]
                if p.is_completed:
                    self.completedProjectsCache[key] = p
        return self.completedProjectsCache

    def get_active_projects(self):
        if not self.activeProjectsCache:
            self.activeProjectsCache = {}
            for key in self.allProjectsCache:
                p = self.allProjectsCache[key]
                if p.is_active():
                    self.activeProjectsCache[key] = p
        return self.activeProjectsCache

    def get_upcoming_projects(self):
        if not self.upcomingProjectsCache:
            self.upcomingProjectsCache = {}
            for key in self.allProjectsCache:
                p = self.allProjectsCache[key]
                if p.is_upcoming():
                    self.upcomingProjectsCache[key] = p
        return self.upcomingProjectsCache

    def _clear_cached_results(self):
        self.allProjectsCache = None
        self.completedProjectsCache = None
        self.activeProjectsCache = None
        self.upcomingProjectsCache = None

    def get_all_projects(self) -> Mapping[str, Project]:
        if self.allProjectsCache:
            # return cached results
            return self.allProjectsCache

        # fetch from data source
        self._clear_cached_results()
        result = self.dataSource.get_all_projects_as_map()
        if result.wasIntentSuccessful:
            self.allProjectsCache = result.data
            return self.allProjectsCache
        else:
            # TODO log error
            return {}

    def cache_projects_data(self, key: str, data: any):
        self.cache.set_value(key, data)

    def create_contract(self, title: str) -> ProjectIntentsResult:
        result = self.dataSource.create_contract(title)
        if not result.wasIntentSuccessful:
            result.errorMsg = CREATE_CONTRACT_FAILED_ERR
        return result

    def create_client(self, title: str) -> ProjectIntentsResult:
        result = self.dataSource.create_client(title)
        if not result.wasIntentSuccessful:
            result.errorMsg = CREATE_CLIENT_FAILED_ERR
        return result

    def get_all_clients_as_map(self):
        result = self.dataSource.get_all_clients_as_map()
        idClientMap = {}
        if len(result) > 0:
            for key in result:
                item = result[key]
                idClientMap[key] = item.title
        return idClientMap

    def get_all_contracts_as_map(self):
        result = self.dataSource.get_all_contracts_as_map()
        idContractMap = {}
        if len(result) > 0:
            for key in result:
                item = result[key]
                idContractMap[key] = item.title
        return idContractMap

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
        self.dataSource.update_contract_client(contractId=contractId, clientId=clientId)
        result = self.dataSource.save_project(
            title=title,
            description=description,
            startDate=startDate,
            endDate=endDate,
            tag=tag,
            clientId=clientId,
            contractId=contractId,
        )
        if not result.wasIntentSuccessful:
            result.errorMsg = CREATE_PROJECT_FAILED
        return result

    def get_project_by_id(self, projectId) -> ProjectIntentsResult:
        projectIfFound = self.dataSource.get_project_by_id(projectId=projectId)
        return ProjectIntentsResult(
            wasIntentSuccessful=projectIfFound is not None,
            data=projectIfFound,
            errorMsgIfAny=PROJECT_NOT_FOUND if projectIfFound is None else "",
        )
