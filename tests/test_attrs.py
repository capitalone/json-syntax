import pytest

from .common import SoftMod, typing as t, Rules
from .types_attrs_common import Hooks, T, U

from json_syntax import attrs as at
from json_syntax import std
from json_syntax.helpers import JSON2PY, PY2JSON, INSP_PY, INSP_JSON

import attr
from collections import namedtuple
from typing import Tuple, Generic, List

ann = SoftMod("tests.types_attrs_ann", allow_SyntaxError=True)


@attr.s
class Flat:
    a = attr.ib(type=int)
    b = attr.ib("default", type=str)


@attr.s
class GenFlat(Generic[T]):
    a = attr.ib(type=T)
    b = attr.ib("default", type=str)


@attr.s
class PrivateFields:
    pub = attr.ib(type=str)
    _priv = attr.ib(type=int)


@attr.s
class Hook1(Hooks):
    a = attr.ib(type=int)
    b = attr.ib("default", type=str)


@attr.s
class GenExample(Generic[T, U]):
    body = attr.ib(type=T)
    count = attr.ib(type=int)
    messages = attr.ib(type=t.List[U])


try:

    @attr.s(slots=True)
    class GenExampleSlots(Generic[T, U]):
        body = attr.ib(type=T)
        count = attr.ib(type=int)
        messages = attr.ib(type=t.List[U])


except TypeError:
    GenExampleSlots = None


class Fail:
    def lookup(self, verb, typ, accept_missing):
        raise RuntimeError("Should not be called in this test")


class Ctx:
    def lookup(self, verb, typ, accept_missing):
        if typ is None:
            raise RuntimeError("Should not be called with typ=None")

        if verb in (JSON2PY, PY2JSON):
            return typ
        else:
            return lambda val: isinstance(val, typ)


def test_attrs_classes_disregards():
    "Test that attrs_classes disregards unknown verbs and types."

    assert at.attrs_classes(verb=PY2JSON, typ=int, ctx=Fail()) is None
    assert at.attrs_classes(verb=INSP_PY, typ=int, ctx=Fail()) is None
    assert at.attrs_classes(verb=JSON2PY, typ=object, ctx=Fail()) is None
    assert at.attrs_classes(verb="dummy", typ=Flat, ctx=Fail()) is None


@pytest.mark.parametrize(
    "con, FlatCls",
    [
        (Flat, Flat),
        (ann.Flat, ann.Flat),
        (GenFlat, GenFlat[int]),
        (ann.GenFlat, ann.GenFlat[int]) if ann.GenFlat else (None, None),
        (ann.FlatDc, ann.FlatDc),
        (ann.GenFlatDc, ann.GenFlatDc[int]) if ann.GenFlatDc else (None, None),
    ],
)
def test_attrs_encoding(con, FlatCls):
    "Test that attrs_classes encodes and decodes a flat class."
    if FlatCls is None:
        pytest.skip("Annotations unavailable")

    encoder = at.attrs_classes(verb=PY2JSON, typ=FlatCls, ctx=Ctx())
    assert encoder(con(33, "foo")) == {"a": 33, "b": "foo"}
    assert encoder(con(33, "default")) == {"a": 33}

    decoder = at.attrs_classes(verb=JSON2PY, typ=FlatCls, ctx=Ctx())
    assert decoder({"a": 33, "b": "foo"}) == FlatCls(33, "foo")
    assert decoder({"a": 33}) == FlatCls(33)

    inspect = at.attrs_classes(verb=INSP_PY, typ=FlatCls, ctx=Ctx())
    assert inspect(con(33, "foo"))
    assert inspect(con("str", "foo"))
    assert not inspect({"a": 33, "b": "foo"})

    inspect = at.attrs_classes(verb=INSP_JSON, typ=FlatCls, ctx=Ctx())
    assert not inspect(con(33, "foo"))
    assert not inspect({"a": "str", "b": "foo"})
    assert inspect({"a": 33})
    assert inspect({"a": 33, "b": "foo"})
    assert not inspect({"b": "foo"})


@pytest.mark.parametrize("PrivateCls", [PrivateFields, ann.PrivateFieldsDc,])
def test_attrs_private(PrivateCls):
    "Test that attrs_classes encode and decode classes with private fields correctly."
    if PrivateCls is None:
        pytest.skip("Annotations unavailable")

    original = PrivateCls("value", 77)

    encoder = at.attrs_classes(verb=PY2JSON, typ=PrivateCls, ctx=Ctx())
    encoded = encoder(original)

    assert encoded["pub"] == "value"
    assert encoded["_priv"] == 77

    decoder = at.attrs_classes(verb=JSON2PY, typ=PrivateCls, ctx=Ctx())
    decoded = decoder(encoded)

    assert decoded == original


@pytest.mark.parametrize("HookCls", [Hook1, ann.Hook])
def test_attrs_hooks(HookCls):
    "Test that attrs_classes enables hooks."
    if HookCls is None:
        pytest.skip("Annotations unavailable")

    encoder = at.attrs_classes(verb=PY2JSON, typ=HookCls, ctx=Ctx())
    assert encoder(HookCls(33, "foo")) == {"_type_": "Hook", "a": 33, "b": "foo"}
    assert encoder(HookCls(33, "default")) == {"_type_": "Hook", "a": 33}

    decoder = at.attrs_classes(verb=JSON2PY, typ=HookCls, ctx=Ctx())
    assert decoder([33, "foo"]) == HookCls(33, "foo")
    assert decoder({"a": 33, "b": "foo"}) == HookCls(33, "foo")
    assert decoder({"a": 33}) == HookCls(33)

    inspect = at.attrs_classes(verb=INSP_PY, typ=HookCls, ctx=Ctx())
    assert inspect(HookCls(33, "foo"))
    assert inspect(HookCls("str", "foo"))
    assert not inspect({"a": 33, "b": "foo"})

    inspect = at.attrs_classes(verb=INSP_JSON, typ=HookCls, ctx=Ctx())
    assert inspect({"_type_": "Hook", "a": "str", "b": "foo"})
    assert not inspect({"a": 33, "b": "foo"})
    assert inspect({"_type_": "Hook", "a": 33, "b": "foo"})
    assert inspect({"_type_": "Hook"})


@pytest.mark.parametrize(
    "GenClass",
    [
        GenExample,
        GenExampleSlots,
        ann.GenExample,
        ann.GenExampleSlots,
        ann.GenExampleDc,
    ],
)
def test_attrs_generic(GenClass):
    if GenClass is None:
        pytest.skip()

    @attr.s
    class Top:
        nested = attr.ib(type=GenClass[GenClass[str, str], str])
        list_of = attr.ib(type=List[GenClass[Tuple[Flat, ...], int]])

    rules = Rules(at.attrs_classes, std.atoms, std.lists)
    py_val = Top(
        nested=GenClass(
            body=GenClass(body="body", count=5, messages=["msg1", "msg2"]),
            count=3,
            messages=["msg3", "msg4"],
        ),
        list_of=[
            GenClass(body=(Flat(a=1), Flat(a=2, b="three")), count=4, messages=[6, 7])
        ],
    )
    j_val = {
        "list_of": [
            {"body": [{"a": 1}, {"a": 2, "b": "three"}], "count": 4, "messages": [6, 7]}
        ],
        "nested": {
            "body": {"body": "body", "count": 5, "messages": ["msg1", "msg2"]},
            "count": 3,
            "messages": ["msg3", "msg4"],
        },
    }

    encoder = at.attrs_classes(verb=PY2JSON, typ=Top, ctx=rules)
    assert encoder(py_val) == j_val

    decoder = at.attrs_classes(verb=JSON2PY, typ=Top, ctx=rules)
    assert decoder(j_val) == py_val

    inspect = at.attrs_classes(verb=INSP_PY, typ=Top, ctx=rules)
    assert inspect(py_val)

    inspect = at.attrs_classes(verb=INSP_JSON, typ=Top, ctx=rules)
    assert inspect(j_val)


class Ctx2:
    def lookup(self, *, verb, typ, accept_missing=False):
        if typ is None:
            assert accept_missing, "typ is None without accept_missing"
            if verb in (JSON2PY, PY2JSON):
                return str
            else:
                return lambda val: isinstance(val, str)

        if verb in (JSON2PY, PY2JSON):
            return typ
        else:
            return lambda val: isinstance(val, typ)


def test_named_tuples_disregards():
    "Test that named_tuples disregards unknown verbs and types."

    assert at.named_tuples(verb=PY2JSON, typ=int, ctx=Fail()) is None
    assert at.named_tuples(verb=INSP_PY, typ=int, ctx=Fail()) is None
    assert at.named_tuples(verb=JSON2PY, typ=tuple, ctx=Fail()) is None
    assert at.named_tuples(verb="dummy", typ=Named1, ctx=Fail()) is None


Named1 = namedtuple("Named1", ["a", "b"])
try:
    Named2 = namedtuple("Named2", ["a", "b"], defaults=["default"])
except TypeError:
    Named2 = None
Named3 = ann.Named


def test_named_tuples_encoding1():
    "Test that named_tuples encodes and decodes a namedtuple."

    encoder = at.named_tuples(verb=PY2JSON, typ=Named1, ctx=Ctx2())
    assert encoder(Named1(42, "foo")) == {"a": "42", "b": "foo"}

    decoder = at.named_tuples(verb=JSON2PY, typ=Named1, ctx=Ctx2())
    assert decoder({"a": 42, "b": "foo"}) == Named1("42", "foo")


@pytest.mark.skipif(Named2 is None, reason="defaults arg to namedtuple unavailable")
def test_named_tuples_encoding2():
    "Test that named_tuples encodes and decodes a namedtuple."

    encoder = at.named_tuples(verb=PY2JSON, typ=Named2, ctx=Ctx2())
    assert encoder(Named2(42, "foo")) == {"a": "42", "b": "foo"}
    assert encoder(Named2(42)) == {"a": "42"}

    decoder = at.named_tuples(verb=JSON2PY, typ=Named2, ctx=Ctx2())
    assert decoder({"a": 42, "b": "foo"}) == Named2("42", "foo")
    assert decoder({"a": 42}) == Named2("42")


@pytest.mark.skipif(Named3 is None, reason="annotations unavailable")
def test_named_tuples_encoding3():
    "Test that named_tuples encodes and decodes a namedtuple."

    encoder = at.named_tuples(verb=PY2JSON, typ=Named3, ctx=Ctx2())
    assert encoder(Named3(42, "foo")) == {"a": 42, "b": "foo"}
    assert encoder(Named3(42)) == {"a": 42}

    decoder = at.named_tuples(verb=JSON2PY, typ=Named3, ctx=Ctx2())
    assert decoder({"a": 42, "b": "foo"}) == Named3(42, "foo")
    assert decoder({"a": 42}) == Named3(42)


def test_named_tuples_checking1():
    "Test that named_tuples verifies a namedtuple."
    inspect = at.named_tuples(verb=INSP_PY, typ=Named1, ctx=Ctx2())
    assert inspect(Named1(42, "foo"))
    assert inspect(Named1("str", "foo"))
    assert not inspect({"a": "42", "b": "foo"})

    inspect = at.named_tuples(verb=INSP_JSON, typ=Named1, ctx=Ctx2())
    assert not inspect(Named1(42, "foo"))
    assert not inspect({"a": "42"})
    assert not inspect({"a": 42, "b": "foo"})
    assert inspect({"a": "42", "b": "foo"})
    assert not inspect({"b": "foo"})


@pytest.mark.skipif(Named2 is None, reason="defaults arg to namedtuple unavailable")
def test_named_tuples_checking2():
    "Test that named_tuples verifies a namedtuple."
    inspect = at.named_tuples(verb=INSP_PY, typ=Named2, ctx=Ctx2())
    assert inspect(Named2(42, "foo"))
    assert inspect(Named2("str", "foo"))
    assert not inspect({"a": "42", "b": "foo"})

    inspect = at.named_tuples(verb=INSP_JSON, typ=Named2, ctx=Ctx2())
    assert not inspect(Named2(42, "foo"))
    assert not inspect({"a": None, "b": "foo"})
    assert inspect({"a": "42"})
    assert inspect({"a": "42", "b": "foo"})
    assert not inspect({"b": "foo"})


@pytest.mark.skipif(Named3 is None, reason="annotations unavailable")
def test_named_tuples_checking3():
    "Test that named_tuples verifies a namedtuple."
    inspect = at.named_tuples(verb=INSP_PY, typ=Named3, ctx=Ctx2())
    assert inspect(Named3(42, "foo"))
    assert inspect(Named3("str", "foo"))
    assert not inspect({"a": 42, "b": "foo"})

    inspect = at.named_tuples(verb=INSP_JSON, typ=Named3, ctx=Ctx2())
    assert not inspect(Named3(42, "foo"))
    assert not inspect({"a": None, "b": "foo"})
    assert inspect({"a": 42})
    assert inspect({"a": 42, "b": "foo"})
    assert not inspect({"b": "foo"})


def test_tuples_disregards():
    "Test that tuples disregards unknown verbs and types."

    assert at.tuples(verb=PY2JSON, typ=Tuple[int, ...], ctx=Fail()) is None
    assert at.tuples(verb=INSP_PY, typ=int, ctx=Fail()) is None
    assert at.tuples(verb="dummy", typ=Tuple[int, str], ctx=Fail()) is None


def test_tuples_encoding():
    "Test that tuples encodes and decodes a flat class."

    encoder = at.tuples(verb=PY2JSON, typ=Tuple[int, str], ctx=Ctx2())
    assert encoder((33, "foo")) == [33, "foo"]

    decoder = at.tuples(verb=JSON2PY, typ=Tuple[int, str], ctx=Ctx2())
    assert decoder([33, "foo"]) == (33, "foo")

    inspect = at.tuples(verb=INSP_PY, typ=Tuple[int, str], ctx=Ctx2())
    assert inspect((33, "foo"))
    assert not inspect(("str", "foo"))
    assert not inspect((33, "foo", None))

    inspect = at.tuples(verb=INSP_JSON, typ=Tuple[int, str], ctx=Ctx2())
    assert inspect([33, "foo"])
    assert not inspect(["str", "foo"])
    assert not inspect([33, "foo", None])
    assert not inspect({})


@pytest.mark.parametrize(
    "dict_type", [t.TypedDict("Dict1", a=int, b=str) if t.TypedDict else None, ann.Dict]
)
def test_typed_dict_encoding(dict_type):
    "Test that typed_dicts encodes and decodes a typed dict."
    if dict_type is None:
        pytest.skip("TypedDict or annotations unavailable")

    encoder = at.typed_dicts(verb=PY2JSON, typ=dict_type, ctx=Ctx())
    assert encoder({"a": 3, "b": "foo"}) == {"a": 3, "b": "foo"}
    assert encoder({"a": 3, "b": "foo", "c": "extra"}) == {"a": 3, "b": "foo"}
    assert encoder({"a": 3.2, "b": 5}) == {"a": 3, "b": "5"}

    decoder = at.typed_dicts(verb=JSON2PY, typ=dict_type, ctx=Ctx())
    assert decoder({"a": 3, "b": "foo"}) == {"a": 3, "b": "foo"}
    assert decoder({"a": 3, "b": "foo", "c": "extra"}) == {"a": 3, "b": "foo"}
    assert decoder({"a": 3.2, "b": 5}) == {"a": 3, "b": "5"}

    inspect = at.typed_dicts(verb=INSP_PY, typ=dict_type, ctx=Ctx())
    assert inspect({"a": 3, "b": "foo"})
    assert not inspect({"a": 3.2, "b": False})
    assert not inspect("foo")
    assert not inspect({})
    assert inspect({"a": 3, "b": "foo", "c": True})

    inspect = at.typed_dicts(verb=INSP_JSON, typ=dict_type, ctx=Ctx())
    assert inspect({"a": 3, "b": "foo"})
    assert not inspect({"a": 3.2, "b": False})
    assert not inspect("foo")
    assert not inspect({})
    assert inspect({"a": 3, "b": "foo", "c": True})
