from abc import ABC


class IntentResult(ABC):
    """An absraction that defines the result of a view's intent"""

    def __init__(
        self, data, wasIntentSuccessful: bool, errorMsgIfAny: str, logMsg: str
    ):
        super().__init__()
        self.errorMsg = errorMsgIfAny
        self.data = data
        self.wasIntentSuccessful = wasIntentSuccessful
        self.logMsg = logMsg
