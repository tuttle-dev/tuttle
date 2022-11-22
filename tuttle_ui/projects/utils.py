from core.abstractions import IntentResult


class ProjectIntentsResult(IntentResult):
    """Wrapper for results of executed project intents"""

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
