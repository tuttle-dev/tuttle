from core.abstractions import ClientStorage
from flet import Page
import time, threading


class ClientStorageImpl(ClientStorage):
    """Flet's client storage API allows storing key-value data on a client side in a persistent storage"""

    def __init__(self, page: Page):
        super().__init__()
        self.page = page

    def set_value(self, key: str, value: any):
        prefixedKey = self.keys_prefix + key
        self.th = threading.Thread(
            target=lambda: self.page.client_storage.set(prefixedKey, value),
            args=(),
            daemon=True,
        )
        self.th.start()

    def get_value(self, key: str):
        prefixedKey = self.keys_prefix + key
        keyExists = self.page.client_storage.contains_key(prefixedKey)
        if not keyExists:
            return None
        return self.page.client_storage.get(prefixedKey)

    def remove_value(self, key: str):
        prefixedKey = self.keys_prefix + key
        keyExists = self.page.client_storage.contains_key(prefixedKey)
        if keyExists:
            self.page.client_storage.remove(prefixedKey)
