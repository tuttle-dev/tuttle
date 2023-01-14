from core.abstractions import ClientStorage
from flet import Page
import time, threading
from loguru import logger


class ClientStorageImpl(ClientStorage):
    """Flet's client storage API allows storing key-value data on a client side in a persistent storage"""

    def __init__(self, page: Page):
        super().__init__()
        self.page = page
        self.pending_saving_data_key = None
        self.pending_saving_value = None

    def save_value(
        self,
    ):
        self.page.client_storage.set(
            self.pending_saving_data_key, self.pending_saving_value
        )
        # clear
        self.pending_saving_data_key = None
        self.pending_saving_value = None

    def set_value(self, key: str, value: any):
        # TODO fix bug assert jv is not None
        try:
            prefixedKey = self.keys_prefix + key
            self.pending_saving_data_key = prefixedKey
            self.pending_saving_value = value
            self.th = threading.Thread(
                target=self.save_value,
                args=(),
                daemon=True,
            )
            self.th.start()
        except Exception as e:
            logger.error(
                f"ClientStorageImpl.set_value threw an exception {e.__class__.__name__}"
            )
            logger.exception(e)

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

    def clear_preferences(self):
        try:
            self.page.client_storage.clear()
        except Exception as e:
            logger.error(
                f"Exception raised @ClientStorageImpl.clear_preferences {e.__class__.__name__}"
            )
            logger.exception(e)
