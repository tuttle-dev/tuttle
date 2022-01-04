"""Cloud connectors."""

import getpass
import pyicloud


def login_iCloud():
    """Log in to Apple iCloud"""
    user_name = getpass.getpass(prompt="iCloud user: ")
    password = getpass.getpass(prompt="iCloud password: ")
    iCloud = pyicloud.PyiCloudService(user_name, password)
    if not iCloud.is_trusted_session:
        result = iCloud.validate_2fa_code(getpass.getpass(prompt="verification code: "))
    assert iCloud.is_trusted_session
    return iCloud
