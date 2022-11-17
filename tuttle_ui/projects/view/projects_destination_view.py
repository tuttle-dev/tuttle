from flet import (UserControl, Text)

class ProjectsDestinationView(UserControl):
    def __init__(self):
        super().__init__()

    def build(self):
        view = Text("Projects View")
        return view