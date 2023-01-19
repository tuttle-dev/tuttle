"""defines misc utils used in resource files"""

import warnings

warnings.warn(
    "wastebasket module, content should be moved to other modules",
    DeprecationWarning,
    stacklevel=2,
)

# route names
SPLASH_SCREEN_ROUTE = "/"
HOME_SCREEN_ROUTE = "/home"

PROJECT_EDITOR_SCREEN_ROUTE = "/edit_project"


CONTRACT_EDITOR_SCREEN_ROUTE = "/edit_contract"


PROJECT_DETAILS_SCREEN_ROUTE = "/project_view"
CONTRACT_DETAILS_SCREEN_ROUTE = "/contract_view"

PROFILE_SCREEN_ROUTE = "/profile"
PREFERENCES_SCREEN_ROUTE = "/preferences"

# intents
ADD_CLIENT_INTENT = "/new_client"
ADD_CONTACT_INTENT = "/new_contact"
NEW_TIME_TRACK_INTENT = "/new_timetrack"
CREATE_INVOICE_INTENT = "/new_invoice"
