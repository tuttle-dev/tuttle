import flet
from flet import (
    UserControl,TextField,Column, padding, TextStyle
)

from res import strings, spacing, fonts, colors
from core.ui.components.text import textfields

class LoginForm(UserControl):
    def __init__(self):
        super().__init__()

    def build(self):

        nameField = textfields.getStdTxtField(strings.nameLbl, strings.nameHint, 'name')
        emailField = textfields.getStdTxtField(strings.emailLbl, strings.emailHint, 'email')

        form = Column(
            spacing=spacing.SPACE_MD,
            controls=[
                nameField,
                emailField
            ]
        )

        return form