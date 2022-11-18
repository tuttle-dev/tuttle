from abc import ABC, abstractmethod
from .data_source import DataSource
from core.abstractions.local_cache import LocalCache


class Intent(ABC):
    """A simple abstraction that defines an intent class

    cache - provides access to local/client storage
    dataSource - provides access to the data dataSource
    """

    def __init__(self, cache: LocalCache, dataSource: DataSource):
        super().__init__()
        self.cache = cache
        self.dataSource = dataSource
