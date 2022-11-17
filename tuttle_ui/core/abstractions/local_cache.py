from abc import ABC, abstractmethod
import typing

class LocalCache(ABC):
    """An abstraction that defines methods for caching data"""
    def __init__(self,):
        super().__init__()
        self.tuttleKeysPrefix = "tuttle"

    @abstractmethod
    def set_value(self, key : str, value : any):
        """appends an identifier prefix to the key and stores the key-value pair
        value can be a string, number, boolean or list
        """
        pass

    @abstractmethod
    def get_value(self, key :  str) -> typing.Optional[any]:
        """appends an identifier prefix to the key and gets the value if exists"""
        pass 

    @abstractmethod
    def remove_value(self, key :  str):
        """appends an identifier prefix to the key and removes associated key-value pair if exists"""
        pass