"""Cloud connectors."""

from typing import Optional, Union, Any

from enum import Enum

from loguru import logger
import getpass
import icloudpy
from icloudpy import ICloudPyService
from .model import ICloudAccount, GoogleAccount
from dataclasses import dataclass


class CloudProvider(Enum):
    Google = "Google"
    ICloud = "iCloud"

    def __str__(self) -> str:
        return str(self.value)


class CloudConnector:
    """Wraps and abstracts the cloud API connection objects of various cloud providers"""

    def __init__(
        self,
        cloud_connector: Union[icloudpy.ICloudPyService, Any],
    ):
        self.concrete_connector = cloud_connector

    @property
    def provider(self) -> str:
        """Returns the cloud provider name"""
        if isinstance(self.concrete_connector, icloudpy.ICloudPyService):
            return "iCloud"
        else:
            return "Unknown"

    @property
    def requires_2fa(self) -> bool:
        """Returns True if the cloud connector requires 2fa"""
        if isinstance(self.concrete_connector, icloudpy.ICloudPyService):
            return self.concrete_connector.is_trusted_session == False
        else:
            raise NotImplementedError

    @property
    def is_connected():
        if isinstance(self.concrete_connector, icloudpy.ICloudPyService):
            return icloud_connector.is_trusted_session
        else:
            raise NotImplementedError

    def validate_2fa_code(
        self,
        twofa_code: str,
    ):
        """Validates a 2fa code for the cloud connector"""
        if isinstance(self.cloud_connector, icloudpy.ICloudPyService):
            icloud_connector: icloudpy.ICloudPyService = self.concrete_connector
            icloud_connector.validate_2fa_code(twofa_code)
        else:
            raise NotImplementedError
