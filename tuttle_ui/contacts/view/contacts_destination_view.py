from flet import (UserControl, Text)

class ContactsDestinationView(UserControl):
    def __init__(self):
        super().__init__()

    def build(self):
        view = Text("Contacts View")
        return view