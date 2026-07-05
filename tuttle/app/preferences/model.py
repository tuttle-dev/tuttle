from dataclasses import dataclass
from enum import Enum

INVOICE_TEMPLATES = {
    "invoice-modern": "Modern",
    "invoice-minimal": "Minimal",
    "invoice-bold": "Bold",
    "invoice-grayshades": "Grayshades",
}

SUPPORTED_INVOICE_LANGUAGES = {
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
}

DEFAULT_INVOICE_TEMPLATE = "invoice-modern"

INVOICE_NUMBER_SCHEMES = {
    "daily": "YYYY-MM-DD-NN (daily sequence)",
    "yearly": "YYYY-NN (yearly sequence)",
    "plain": "NN (plain auto-increment)",
}

DEFAULT_INVOICE_NUMBER_SCHEME = "daily"

E_INVOICE_PROFILES = {
    "": "Off (plain PDF only)",
    "EN16931": "Standard (recommended)",
    "XRECHNUNG": "XRechnung (German public sector)",
    "BASIC": "Basic (minimal data)",
    "EXTENDED": "Extended (full detail)",
}

DEFAULT_E_INVOICE_PROFILE = "EN16931"

DEFAULT_INCLUDE_LOGO = True

DEFAULT_INCLUDE_DUE_DATE = True

DEFAULT_THEME_MODE = "system"


@dataclass
class Preferences:
    theme_mode: str = ""
    language: str = ""
    invoice_template: str = DEFAULT_INVOICE_TEMPLATE
    invoice_number_scheme: str = DEFAULT_INVOICE_NUMBER_SCHEME
    e_invoice_profile: str = DEFAULT_E_INVOICE_PROFILE
    include_logo: bool = DEFAULT_INCLUDE_LOGO
    include_due_date: bool = DEFAULT_INCLUDE_DUE_DATE


class PreferencesStorageKeys(Enum):
    """defines the keys used in storing preferences as key-value pairs"""

    theme_mode_key = "preferred_theme_mode"
    language_key = "preferred_language"
    invoice_template_key = "preferred_invoice_template"
    invoice_number_scheme_key = "preferred_invoice_number_scheme"
    e_invoice_profile_key = "preferred_e_invoice_profile"
    include_logo_key = "preferred_include_logo"
    include_due_date_key = "preferred_include_due_date"

    def __str__(self) -> str:
        return str(self.value)
