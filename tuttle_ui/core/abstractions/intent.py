from abc import ABC, abstractmethod
from .model import Model

class Intent(ABC):
    """A simple abstraction that defines an intent class"""
    def __init__(self):
        super().__init__()

    @abstractmethod
    def set_model(self, model : Model):
        """sets the model for this intent """
        pass

