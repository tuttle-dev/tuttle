from typing import Mapping
from abc import ABC, abstractmethod

from core.abstractions import ClientStorage
from core.models import IntentResult

from .model import TimeTrackingDataSource, TimeTrackingDataSourceImpl


class TimeTrackingIntent(ABC):
    """Handles client view intents"""

    def __init__(
        self,
        data_source: TimeTrackingDataSource,
        local_storage: ClientStorage,
    ):
        super().__init__()
        self.local_storage = local_storage
        self.data_source = data_source


class TimeTrackingIntentImpl(TimeTrackingIntent):
    def __init__(self, local_storage: ClientStorage):
        super().__init__(
            data_source=TimeTrackingDataSourceImpl(client_storage=local_storage),
            local_storage=local_storage,
        )
