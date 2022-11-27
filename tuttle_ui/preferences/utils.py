from core.abstractions import IntentResult


class PreferencesIntentsResult(IntentResult):
    """Wrapper for results of executed preferences intents"""

    def __init__(
        self,
        data=None,
        wasIntentSuccessful: bool = False,
        errorMsgIfAny: str = "",
        logMsg: str = "",
    ):
        super().__init__(
            data=data,
            wasIntentSuccessful=wasIntentSuccessful,
            errorMsgIfAny=errorMsgIfAny,
            logMsg=logMsg,
        )
