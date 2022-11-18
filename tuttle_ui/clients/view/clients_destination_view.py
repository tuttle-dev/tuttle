from flet import UserControl, Text


class ClientsDestinationView(UserControl):
    def __init__(self):
        super().__init__()

    def build(self):
        view = Text("Clients View")
        return view
