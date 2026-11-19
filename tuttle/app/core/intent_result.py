import annotationlib
import functools
import inspect
from typing import Callable, Generic, Optional, TypeVar

from loguru import logger

T = TypeVar("T")


class IntentResult(Generic[T]):
    """Wraps the result of a view's intent and self logs

    Methods
    -------
    log_message()
        Logs the log_message and exception if any

    Params:
        data - payload if any else None, the type of data will be specified at instantiation
        was_intent_successful - True if no error or exception was raised, else False
        error_msg - message to display to the user
        warning - non-fatal issue to surface to the user (e.g. render failure on an otherwise saved invoice)
        log_message - message to log for debugging
        exception - exception object for debugging
    """

    def __init__(
        self,
        data: Optional[T] = None,
        was_intent_successful: bool = False,
        error_msg: str = "",
        warning: str = "",
        log_message: str = "",
        exception: Optional[Exception] = None,
    ):
        super().__init__()
        self.error_msg = error_msg
        self.warning = warning
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


def fails_with(message: str, *, append_exception: bool = False) -> Callable[[Callable], Callable]:
    """Decorate a handler so that an exception it lets escape becomes a failed ``IntentResult``.

    ``message`` is what the user is shown (``error_msg``). With
    ``append_exception`` the text of the exception follows it:
    ``"<message>: <exception>"``. The exception is attached to the result,
    and ``log_message`` names the handler.

    Whatever the handler returns is passed through, so it can still return a
    failed result of its own for a case it recognises.

    The handler keeps its signature, which the dispatcher reads to bind the
    RPC params. A call whose arguments don't fit it raises ``TypeError`` as
    it would undecorated: that is a mistake of the caller, not a failure of
    the handler.
    """

    def decorate(handler: Callable) -> Callable:
        # As strings: the annotations may name a class the module defines further down.
        signature = inspect.signature(handler, annotation_format=annotationlib.Format.STRING)

        @functools.wraps(handler)
        def wrapper(*args, **kwargs):
            signature.bind(*args, **kwargs)
            try:
                return handler(*args, **kwargs)
            except Exception as e:
                return IntentResult(
                    was_intent_successful=False,
                    error_msg=f"{message}: {e}" if append_exception else message,
                    log_message=f"{handler.__qualname__}: {e}",
                    exception=e,
                )

        return wrapper

    return decorate
