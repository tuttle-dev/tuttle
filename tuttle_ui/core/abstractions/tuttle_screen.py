from abc import ABC, abstractmethod

class TuttleScreen(ABC):
    def __init__(self, hasFloatingActionBtn, hasAppBar):
        self.hasFloatingActionBtn = hasFloatingActionBtn,
        self.hasAppBar = hasAppBar,
        super().__init__()

    @abstractmethod
    def getFloatingActionBtnIfAny(self):
        pass

    @abstractmethod
    def getAppBarIfAny(self):
        pass

   