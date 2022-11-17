from core.abstractions.local_cache import LocalCache
from flet import Page

# TODO
class LocalCacheImpl(LocalCache):
    """Implements LocalCache"""
    def __init__(self, page : Page):
        super().__init__()
        self.page = page
        self.cacheSim = {}

    def set_value(self, key : str, value : any):
        prefixedKey = self.tuttleKeysPrefix + key
        self.cacheSim[prefixedKey] = value

    def get_value(self, key :  str):
        prefixedKey = self.tuttleKeysPrefix + key
        keyExists = prefixedKey in self.cacheSim.keys()
        if not keyExists:
            return None
        return self.cacheSim[prefixedKey]  

    def remove_value(self, key :  str):
        prefixedKey = self.tuttleKeysPrefix + key
        if prefixedKey in self.cacheSim:
            del self.cacheSim[prefixedKey]