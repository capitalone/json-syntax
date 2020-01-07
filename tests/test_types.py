import pytest

from json_syntax import types as tt

from .common import typing as t, SoftMod
from .types_attrs_common import T, U

import attr

ann = SoftMod("tests.types_attrs_ann", allow_SyntaxError=True)


@attr.s
class GenExample(t.Generic[T, U]):
    body = attr.ib(type=T)
    count = attr.ib(type=int)
    messages = attr.ib(type=t.List[U])


def test_has_origin_not_typing():
    "Test that has_origin disregards a type value if it's not from `typing`."

    assert tt.has_origin(list, list)


def test_has_origin_handle_tuple():
    "Test that has_origin accepts a tuple of origins."

    assert tt.has_origin(t.List[int], (str, list, tuple))


def test_has_origin_num_args():
    "Test that has_origin checks the number of arguments."

    assert tt.has_origin(t.Tuple[int, str, float], tuple, num_args=3)


def test_issub_safe_normal_type1():
    "Test that issub_safe behaves like issubclass for normal types."

    assert tt.issub_safe(bool, int)
    assert tt.issub_safe(bool, (int, float, str))
    assert not tt.issub_safe(int, str)


def test_issub_safe_normal_type2():
    "Test that issub_safe returns False for generic types."

    assert not tt.issub_safe(t.List[int], list)


def test_eval_type_imports():
    "Test that the private ``typing._eval_type`` function imports."

    assert (
        tt._eval_type is not None
    ), "typing._eval_type is not available, investigate an alternative."


class SomeClass:
    some_type = t.List["AnotherClass"]


class AnotherClass:
    pass


def test_resolve_fwd_ref():
    "Test that resolve_fwd_ref correctly identifies the target of a forward reference."

    actual = tt.resolve_fwd_ref(SomeClass.some_type, SomeClass)

    assert tt.has_origin(actual, list)
    assert actual.__args__ == (AnotherClass,)


def test_resolve_fwd_ref_bad_context():
    "Test that resolve_fwd_ref returns the original if the module can't be determined."

    try:
        Forward = t.ForwardRef
    except AttributeError:
        Forward = t._ForwardRef
    subj = Forward("AnotherClass")
    actual = tt.resolve_fwd_ref(subj, "dummy")

    assert actual is subj


@pytest.mark.parametrize(
    "GenClass, origin",
    [
        (GenExample, None),
        (GenExample[str, int], GenExample),
        (t.List[int], t.List),
        (t.List["int"], t.List),
        (t.List, None),
        (t.Union[int, str], None),
        (int, None),
    ],
)
def test_get_generic_origin(GenClass, origin):
    "Test that get_generic_origin finds the origin class, unless the class is not generic."
    assert tt.get_generic_origin(GenClass) == origin


@pytest.mark.parametrize(
    "GenClass, origin",
    [
        (GenExample, GenExample),
        (GenExample[str, int], GenExample),
        (t.List[int], list),
        (t.List["int"], list),
        (t.List, list),
        (t.Union[int, str], t.Union),
        (t.Union, t.Union),
        (int, int),
    ],
)
def test_get_origin(GenClass, origin):
    "Test that get_generic_origin finds the origin class, unless the class is not generic."
    assert tt.get_origin(GenClass) == origin
