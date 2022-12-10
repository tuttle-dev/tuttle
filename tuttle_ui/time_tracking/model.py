from abc import ABC, abstractmethod
from typing import Optional, Mapping

from core.abstractions import ClientStorage
from core.models import IntentResult


class TimeTrackingDataSource(ABC):
    """Defines methods for instantiating, viewing, updating, saving and deleting clients"""

    def __init__(self):
        super().__init__()


class TimeTrackingDataSourceImpl(TimeTrackingDataSource):
    """Implements TimeTrackingDataSource"""

    def __init__(self, client_storage: ClientStorage):
        super().__init__()
        self.client_storage = client_storage
