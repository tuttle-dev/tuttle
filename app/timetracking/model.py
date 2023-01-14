"""Helper models for timetracking"""

from dataclasses import dataclass
from preferences.model import CloudAccounts


@dataclass
class CloudCalendarInfo:
    account: str
    calendar_name: str
    provider: str
    password: str


@dataclass
class CloudConfigurationResult:
    """Used during configuration of a cloud account to mediate steps"""

    request_2fa_code: bool = False
    cloud_acc_configured_successfully: bool = False
    provided_2fa_code_is_invalid: bool = False
    auth_error_occurred: bool = False
    session_ref: any = None
    calendar_loaded_successfully: bool = False
