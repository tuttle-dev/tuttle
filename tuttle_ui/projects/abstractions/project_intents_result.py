from core.abstractions.intent_result import IntentResult


class ProjectIntentsResult(IntentResult):
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
