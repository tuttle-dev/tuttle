import datetime

import faker

from contracts.model import Contract
from core.models import Cycle, IntentResult, TimeUnit
from typing import Optional

from tuttle.model import (
    Client,
    Contract,
    Contact,
    Project,
)


class ProjectDataSource:
    def __init__(self):
        super().__init__()

    def get_all_projects_as_map(
        self,
    ) -> IntentResult:
        projects = self._get_dummy_projects()
        return IntentResult(was_intent_successful=True, data=projects)

    def save_project(
        self,
        contract: Contract,
        title: str,
        description: str,
        unique_tag: str,
        start_date: datetime.date,
        end_date: datetime.date,
        is_completed: bool = False,
        project: Optional[Project] = None,
    ) -> IntentResult:
        return IntentResult(was_intent_successful=True, data=project)

    def get_project_by_id(self, projectId) -> IntentResult:
        try:
            fake = faker.Faker()
            p = self._get_fake_project(fake, int(projectId))
            return IntentResult(was_intent_successful=True, data=p)
        except Exception as e:
            return IntentResult(
                was_intent_successful=False,
                log_message=f"Exception raised @Projects.data_source_impl.get_project_by_id {e}",
                data=None,
            )

    """DUMMY CONTENT BELOW ---  DELETE ALL"""

    def _get_dummy_projects(self):
        fake = faker.Faker()
        projects = {}
        total = 10
        for i in range(total):
            p = self._get_fake_project(fake, i)
            projects[p.id] = p
        return projects

    def _get_fake_project(self, fake, id):
        project_title = fake.bs()
        p = Project(
            id=id,
            contract_id=id * 2,
            title=project_title,
            description=fake.paragraph(nb_sentences=2),
            unique_tag=project_title.split(" ")[0].lower(),
            is_completed=True if id % 2 == 0 else False,
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta((id + 1)),
            contract=self._get_fake_contract(id * 2),
        )
        return p

    def _get_fake_contract(self, i):
        c = Contract(
            id=i,
            client_id=i * 3,
            client=self._get_fake_client(i * 3),
            title=f"Tuttle Ui Development Phase {i}",
            rate=i * 2.2,
            volume=int(i * 3.4),
            currency="usd",
            VAT_rate=i * 0.2,
            billing_cycle=Cycle.hourly,
            term_of_payment=12,
            unit=TimeUnit.hour,
            units_per_workday=i * 2.4,
            is_completed=True if i % 2 == 0 else False,
            signature_date=datetime.date.today(),
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta((i + 1)),
        )
        return c

    def _get_fake_client(self, id):
        fake = faker.Faker(
            ["fr_FR", "en_US", "de_DE", "es_ES", "it_IT", "sv_SE", "zh_CN"]
        )
        return Client(id=id, title=fake.company(), invoicing_contact_id=int(id * 3.142))
