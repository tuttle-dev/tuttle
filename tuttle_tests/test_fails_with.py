"""``fails_with`` turns an exception that escapes a handler into a failed IntentResult."""

import inspect

import pytest

from tuttle.app.core.abstractions import Intent
from tuttle.app.core.dispatch import _call
from tuttle.app.core.intent_result import IntentResult, fails_with


class WidgetsIntent(Intent):
    def __init__(self):
        self.runs = 0

    @fails_with("Failed to load the widget.")
    def load(self, widget_id: int, verbose: bool = False) -> IntentResult:
        """Load one widget."""
        self.runs += 1
        if widget_id < 0:
            return IntentResult(was_intent_successful=False, error_msg="No such widget.")
        if widget_id == 0:
            raise ValueError("the shelf is empty")
        return IntentResult(was_intent_successful=True, data={"id": widget_id}, warning="The widget is dusty.")

    @fails_with("Failed to delete the widget", append_exception=True)
    def delete(self, widget_id: int) -> IntentResult:
        self.runs += 1
        if widget_id == 0:
            raise TypeError("the shelf is empty")
        return IntentResult(was_intent_successful=True, data=widget_id)

    def load_undecorated(self, widget_id: int, verbose: bool = False) -> IntentResult:
        """Load one widget."""


def test_success_passes_through():
    result = WidgetsIntent().load(7)

    assert result.was_intent_successful
    assert result.data == {"id": 7}
    assert result.warning == "The widget is dusty."
    assert result.error_msg == ""
    assert result.exception is None


def test_a_failure_the_handler_returns_itself_passes_through():
    result = WidgetsIntent().load(-1)

    assert not result.was_intent_successful
    assert result.error_msg == "No such widget."
    assert result.exception is None


def test_an_exception_becomes_a_failed_result_with_the_message():
    result = WidgetsIntent().load(0)

    assert not result.was_intent_successful
    assert result.error_msg == "Failed to load the widget."
    assert result.data is None
    assert result.warning == ""
    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == "the shelf is empty"
    assert result.log_message == "WidgetsIntent.load: the shelf is empty"


def test_the_exception_text_is_appended_on_request():
    result = WidgetsIntent().delete(0)

    assert not result.was_intent_successful
    assert result.error_msg == "Failed to delete the widget: the shelf is empty"
    assert isinstance(result.exception, TypeError)


def test_the_handler_keeps_its_signature_name_and_docstring():
    """The dispatcher binds RPC params with ``inspect.signature``."""
    assert inspect.signature(WidgetsIntent.load) == inspect.signature(WidgetsIntent.load_undecorated)
    assert list(inspect.signature(WidgetsIntent().load).parameters) == ["widget_id", "verbose"]
    assert WidgetsIntent.load.__name__ == "load"
    assert WidgetsIntent.load.__doc__ == "Load one widget."


def test_a_call_that_does_not_fit_the_handler_raises_type_error():
    """Not a failure of the handler: it never ran."""
    intent = WidgetsIntent()

    with pytest.raises(TypeError):
        intent.load(widget=7)
    with pytest.raises(TypeError):
        intent.load()

    assert intent.runs == 0


def test_the_dispatcher_binds_params_by_the_handlers_own_signature():
    """A single param takes the only value sent, whatever its name."""
    intent = WidgetsIntent()

    result = _call(intent.delete, {"id": 7})

    assert result.was_intent_successful
    assert result.data == 7
    assert intent.runs == 1


def test_a_handler_may_name_a_class_defined_later_in_its_annotations():
    class ShelvesIntent:
        @fails_with("Failed to load the shelf.")
        def load(self, shelf: Shelf) -> IntentResult[Shelf]:
            return IntentResult(was_intent_successful=True, data=shelf)

    class Shelf:
        pass

    shelf = Shelf()

    assert ShelvesIntent().load(shelf).data is shelf


def test_a_type_error_inside_the_handler_is_a_failure_of_the_handler():
    intent = WidgetsIntent()

    result = _call(intent.delete, {"widget_id": 0})

    assert not result.was_intent_successful
    assert result.error_msg == "Failed to delete the widget: the shelf is empty"
    assert intent.runs == 1
