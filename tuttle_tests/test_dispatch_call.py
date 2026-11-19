"""How the dispatcher binds RPC params to a handler."""

import pytest

from tuttle.app.core.dispatch import _call


class Handlers:
    def __init__(self):
        self.runs = 0

    def by_id(self, id):
        self.runs += 1
        return id

    def create(self, project_id, note=None):
        self.runs += 1
        return project_id, note

    def failing(self, id):
        self.runs += 1
        raise TypeError("raised inside the handler")

    def failing_create(self, project_id, note=None):
        self.runs += 1
        raise TypeError("raised inside the handler")


@pytest.mark.parametrize(
    "method, params",
    [
        ("failing", {"id": 3}),
        ("failing_create", {"project_id": 7, "note": "x"}),
    ],
)
def test_handler_that_raises_type_error_runs_once(method, params):
    """A TypeError from inside a handler is its own error, not a sign that the params did not fit."""
    handlers = Handlers()

    with pytest.raises(TypeError, match="raised inside the handler"):
        _call(getattr(handlers, method), params)

    assert handlers.runs == 1


@pytest.mark.parametrize(
    "method, params, expected",
    [
        ("by_id", {"id": 3}, 3),
        # A single param takes the only value sent, whatever its name.
        ("by_id", {"invoice_id": 3}, 3),
        ("create", {"project_id": 7, "note": "x"}, (7, "x")),
        # Params the handler does not take are dropped.
        ("create", {"project_id": 7, "unknown": 1}, (7, None)),
    ],
)
def test_params_are_bound_to_the_handler(method, params, expected):
    handlers = Handlers()

    assert _call(getattr(handlers, method), params) == expected
    assert handlers.runs == 1


def test_missing_required_param_is_named():
    with pytest.raises(TypeError, match="project_id"):
        _call(Handlers().create, {"note": "x"})
