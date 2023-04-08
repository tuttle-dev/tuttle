from typing import Optional, Any

import threading


from flet import Page

from core.abstractions import ClientStorage
from loguru import logger


class ClientStorageImpl(ClientStorage):
    """Flet's client storage API allows storing key-value data on a client side in a persistent storage"""

    def __init__(self, page: Page):
        super().__init__()
        self.__page = page

    def set_value(self, key: str, value: Any):
        """appends an identifier prefix to the key and stores the key-value pair
        value can be a string, number, boolean or list
        """
        try:
            threading.Thread(
                target=self.__page.client_storage.set,
                args=(self.keys_prefix + key, value),
            ).start()
        except Exception as e:
            logger.error(
                f"Error while setting client storage value {key} {value}: {e.__class__.__name__}"
            )
            logger.exception(e)

    def get_value(self, key: str) -> Optional[Any]:
        """appends an identifier prefix to the key and gets the value if exists"""
        try:
            return self.__page.client_storage.get(self.keys_prefix + key)
        except Exception as e:
            logger.error(
                f"Error while getting client storage value {key}: {e.__class__.__name__}"
            )
            logger.exception(e)
            return None

    def remove_value(self, key: str):
        """appends an identifier prefix to the key and removes associated key-value pair if exists"""
        try:
            threading.Thread(
                target=self.__page.client_storage.remove, args=(self.keys_prefix + key,)
            ).start()
        except Exception as e:
            logger.error(
                f"Error while removing client storage value {key}: {e.__class__.__name__}"
            )
            logger.exception(e)

    def clear_preferences(self):
        """Deletes all of preferences permanently"""
        try:
            threading.Thread(target=self.__page.client_storage.clear, args=()).start()
        except Exception as e:
            logger.error(f"Error while clearing client storage: {e.__class__.__name__}")
            logger.exception(e)
