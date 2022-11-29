from core.abstractions import ClientStorage
from flet import Page

# TODO - remove the cache with actual local storage
class ClientStorageImpl(ClientStorage):
    """Flet's client storage API allows storing key-value data on a client side in a persistent storage"""

    def __init__(self, page: Page):
        super().__init__()
        self.page = page
        self.cache = {}

    def set_value(self, key: str, value: any):
        prefixedKey = self.keys_prefix + key
        self.cache[prefixedKey] = value

    def get_value(self, key: str):
        prefixedKey = self.keys_prefix + key
        keyExists = prefixedKey in self.cache.keys()
        if not keyExists:
            return None
        return self.cache[prefixedKey]

    def remove_value(self, key: str):
        prefixedKey = self.keys_prefix + key
        if prefixedKey in self.cache:
            del self.cache[prefixedKey]
