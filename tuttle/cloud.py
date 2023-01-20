"""Cloud connectors."""

from typing import Optional
from loguru import logger
import icloudpy
from icloudpy import ICloudPyService
from dataclasses import dataclass
from tuttle.dev import deprecated


@deprecated
@dataclass
class CloudLoginResult:
    """Wraps the result of login in-to a cloud account"""

    request_2fa_code: bool = False
    session: Optional[any] = None
    auth_error_occured: bool = False
    has_invalid_2fa_code: bool = False
    is_logged_in: bool = False


@deprecated
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
            session=iCloud,
        )
    except Exception as e:
        logger.error(
            f"Exception raised @login_iCloud during validation {e.__class__.__name__}"
        )
        logger.exception(e)
        return CloudLoginResult(has_invalid_2fa_code=True, session=iCloud)


@deprecated
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
            session=iCloud,
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


@deprecated
def login_google(
    user_name: str,
    password: str,
    two_factor_auth_code: Optional[str] = None,
) -> CloudLoginResult:
    """TODO implement Log into Google API."""
    return CloudLoginResult(auth_error_occured=True)
