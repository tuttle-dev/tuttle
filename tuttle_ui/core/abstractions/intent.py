from abc import ABC, abstractmethod
from .model import Model
from core.abstractions.local_cache import LocalCache

class Intent(ABC):
    """A simple abstraction that defines an intent class
    
    cache - provides access to local/client storage
    model - provides access to the data model
    """
    def __init__(self, cache : LocalCache, model : Model):
        super().__init__()
        self.cache = cache
        self.model = model
