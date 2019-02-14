from json_syntax import helpers as hlp

import typing as t


def test_identity():
    "Test that the identity function does what it says."

    subj = object()

    assert hlp.identity(subj) is subj


def test_has_origin_not_typing():
    "Test that has_origin disregards a type value if it's not from `typing`."

    assert not hlp.has_origin(list, list)


def test_has_origin_handle_tuple():
    "Test that has_origin accepts a tuple of origins."

    assert hlp.has_origin(t.List[int], (str, list, tuple))


def test_has_origin_num_args():
    "Test that has_origin checks the number of arguments."

    assert hlp.has_origin(t.Tuple[int, str, float], tuple, num_args=3)


def test_issub_safe_normal_type():
    "Test that issub_safe behaves like issubclass for normal types."

    assert hlp.issub_safe(bool, int)
    assert hlp.issub_safe(bool, (int, float, str))
    assert not hlp.issub_safe(int, str)


def test_issub_safe_normal_type():
    "Test that issub_safe returns False for generic types."

    assert not hlp.issub_safe(t.List[int], list)


def test_eval_type_imports():
    "Test that the private ``typing._eval_type`` function imports."

    from json_syntax.helpers import _eval_type

    assert (
        _eval_type is not None
    ), "typing._eval_type is not available, investigate an alternative."


class SomeClass:
    some_type = t.List["AnotherClass"]


class AnotherClass:
    pass


def test_resolve_fwd_ref():
    "Test that resolve_fwd_ref correctly identifies the target of a forward reference."

    actual = hlp.resolve_fwd_ref(SomeClass.some_type, SomeClass)

    assert hlp.has_origin(actual, list)
    assert actual.__args__ == (AnotherClass,)


def test_resolve_fwd_ref_bad_context():
    "Test that resolve_fwd_ref returns the original if the module can't be determined."

    try:
        Forward = t.ForwardRef
    except AttributeError:
        Forward = t._ForwardRef
    subj = Forward("AnotherClass")
    actual = hlp.resolve_fwd_ref(subj, "dummy")

    assert actual is subj
