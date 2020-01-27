import pytest

from json_syntax import errors as err

import traceback as tb


@pytest.mark.parametrize(
    "args,expect",
    [
        ((), "ValueError: At .alpha.beta\n"),
        (("message",), "ValueError: message; at .alpha.beta\n"),
        (("two", "parts"), "ValueError: ('two; at .alpha.beta', 'parts')\n"),
    ],
)
def test_error_context(args, expect):
    "Test that error contexts add information correctly."

    try:
        with err.ErrorContext(".", "alpha"):
            with err.ErrorContext(".", "beta"):
                raise ValueError(*args)
    except ValueError as exc:
        actual = "".join(tb.format_exception_only(type(exc), exc))
    else:
        assert False, "Didn't throw?!"

    assert actual == expect


def test_error_ctx_inline():
    "Test that err_ctx adds inline context."

    def inside():
        raise ValueError("message")

    try:
        err.err_ctx(".alpha", inside)
    except ValueError as exc:
        actual = "".join(tb.format_exception_only(type(exc), exc))
    else:
        assert False, "Didn't throw?!"

    assert actual == "ValueError: message; at .alpha\n"
