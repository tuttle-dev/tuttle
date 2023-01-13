from loguru import logger
from typing import Optional


class IntentResult:
    """Wraps the result of a view's intent and self logs

    Methods
    -------
    log_message()
        Logs the log_message and exception if any

    Params:
        data - payload if any else None
        was_intent_successful - True if no error or exception was raised, else False
        error_msg - message to display to the user
        log_message - message to log for debugging
        exception - exception object for debugging
    """

    def __init__(
        self,
        data: Optional[any] = None,
        was_intent_successful: bool = False,
        error_msg: str = "",
        log_message: str = "",
        exception: Optional[Exception] = None,
    ):
        super().__init__()
        self.error_msg = error_msg
        self.data = data
        self.was_intent_successful = was_intent_successful
        self.log_message = log_message
        self.exception = exception

    def log_message_if_any(self):
        """Logs the log_message and exception if any"""
        if self.log_message:
            logger.error(self.log_message)
        if self.exception:
            logger.exception(self.exception)
