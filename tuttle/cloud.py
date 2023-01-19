"""Cloud connectors."""

from typing import Optional
from loguru import logger
import getpass
import icloudpy
from icloudpy import ICloudPyService
from .model import ICloudAccount, GoogleAccount
from dataclasses import dataclass


@dataclass
class CloudLoginResult:
    """Wraps the result of login in-to a cloud account

    Properties
    ----------
    request_2fa_code : bool
        True if the user should provide an 2fa code before proceeding else False
    icloud_session_ref : ICloudPyService
        Reference to the created icloud session else None
    auth_error_occured : bool
        True if login failed because of invalid auth credentials
    has_invalid_2fa_code : bool
        True if the two factor auth code passed was invalid
    is_logged_in : bool
        True if login was successful
    """

    request_2fa_code: bool = False
    icloud_session_ref: Optional[ICloudPyService] = None
    auth_error_occured: bool = False
    has_invalid_2fa_code: bool = False
    is_logged_in: bool = False


def verify_icloud_session(
    two_factor_auth_code: Optional[str] = None,
    iCloud: Optional[ICloudPyService] = None,
) -> CloudLoginResult:
    """Verify an Apple iCloud session"""
    try:
        iCloud.validate_2fa_code(two_factor_auth_code)
        assert iCloud.is_trusted_session
        return CloudLoginResult(
            is_logged_in=True,
            icloud_session_ref=iCloud,
        )
    except Exception as e:
        logger.error(
            f"Exception raised @login_iCloud during validation {e.__class__.__name__}"
        )
        logger.exception(e)
        return CloudLoginResult(has_invalid_2fa_code=True, icloud_session_ref=iCloud)


def login_iCloud(
    user_name: str,
    password: str,
) -> CloudLoginResult:
    """Log in to Apple iCloud

    Returns
    -------
        CloudLoginResult
            auth_error_occured=True if an auth error occurs e.g. invalid credentials provided
            icloud_session_ref is set if no error occurs
            request_2fa_code = True if user should be asked for a 2fa code before proceeding else False
            is_logged_in = True in case no 2fa code is need else False
    """
    try:
        iCloud = icloudpy.ICloudPyService(apple_id=user_name, password=password)
        request_2fa_code = not iCloud.is_trusted_session
        return CloudLoginResult(
            icloud_session_ref=iCloud,
            request_2fa_code=request_2fa_code,
            is_logged_in=iCloud.is_trusted_session,
        )
    except Exception as e:
        logger.error(
            f"Exception raised @login_iCloud during authentication of {user_name} {e.__class__.__name__}"
        )
        logger.exception(e)
        return CloudLoginResult(
            auth_error_occured=True,
        )


def login_google(
    user_name: str,
    password: str,
    two_factor_auth_code: Optional[str] = None,
) -> CloudLoginResult:
    """TODO implement Log into Google API."""
    return CloudLoginResult(auth_error_occured=True)
