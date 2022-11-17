from flet import (UserControl, Text)

class ContractsDestinationView(UserControl):
    def __init__(self):
        super().__init__()

    def build(self):
        view = Text("Contracts View")
        return view