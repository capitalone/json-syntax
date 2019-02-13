import pytest
from unittest.mock import Mock

from json_syntax import attrs as at
from json_syntax.helpers import J2P, P2J, IP, IJ, JPI, JP, II

import attr
from collections import namedtuple
try:
    from dataclasses import dataclass
except ImportError:
    dataclass = lambda cls: None
from typing import NamedTuple, Tuple

try:
    from tests.types_attrs_ann import flat_types, hook_types
except ImportError:
    from tests.types_attrs_noann import flat_types, hook_types


skip_if = pytest.mark.skip_if
param = pytest.param


class Fail:
    def lookup(self, verb, typ, accept_missing):
        raise RuntimeError("Should not be called in this test")


class Ctx:
    def lookup(self, verb, typ, accept_missing):
        if typ is None:
            raise RuntimeError("Should not be called with typ=None")

        if verb in JP:
            return typ
        else:
            return lambda val: isinstance(val, typ)


def test_attrs_classes_disregards():
    "Test that attrs_classes disregards unknown verbs and types."

    assert at.attrs_classes(verb=P2J, typ=int, ctx=Fail()) is None
    assert at.attrs_classes(verb=IP, typ=int, ctx=Fail()) is None
    assert at.attrs_classes(verb=J2P, typ=object, ctx=Fail()) is None
    assert at.attrs_classes(verb="dummy", typ=Flat1, ctx=Fail()) is None
    assert at.attrs_classes(verb="dummy", typ=Flat2, ctx=Fail()) is None


@skip_if(dataclass is None, "dataclasses not present")
def test_attrs_classes_disregards_dc():
    "Test that attrs_classes disregards dataclass with unknown types."

    assert at.attrs_classes(verb="dummy", typ=Flat2, ctx=Fail()) is None


@pytest.mark.parametrize("FlatCls", flat_types)
def test_attrs_encoding(FlatCls):
    "Test that attrs_classes encodes and decodes a flat class."

    encoder = at.attrs_classes(verb=P2J, typ=FlatCls, ctx=Ctx())
    assert encoder(FlatCls(33, "foo")) == {"a": 33, "b": "foo"}
    assert encoder(FlatCls(33, "default")) == {"a": 33}

    decoder = at.attrs_classes(verb=J2P, typ=FlatCls, ctx=Ctx())
    assert decoder({"a": 33, "b": "foo"}) == FlatCls(33, "foo")
    assert decoder({"a": 33}) == FlatCls(33)

    inspect = at.attrs_classes(verb=IP, typ=FlatCls, ctx=Ctx())
    assert inspect(FlatCls(33, "foo"))
    assert inspect(FlatCls("str", "foo"))
    assert not inspect({"a": 33, "b": "foo"})

    inspect = at.attrs_classes(verb=IJ, typ=FlatCls, ctx=Ctx())
    assert not inspect(FlatCls(33, "foo"))
    assert not inspect({"a": "str", "b": "foo"})
    assert inspect({"a": 33})
    assert inspect({"a": 33, "b": "foo"})
    assert not inspect({"b": "foo"})


@pytest.mark.parametrize("HookCls", hook_types)
def test_attrs_hooks(HookCls):
    "Test that attrs_classes enables hooks."

    encoder = at.attrs_classes(verb=P2J, typ=HookCls, ctx=Ctx())
    assert encoder(HookCls(33, "foo")) == {"_type_": "Hook", "a": 33, "b": "foo"}
    assert encoder(HookCls(33, "default")) == {"_type_": "Hook", "a": 33}

    decoder = at.attrs_classes(verb=J2P, typ=HookCls, ctx=Ctx())
    assert decoder([33, "foo"]) == HookCls(33, "foo")
    assert decoder({"a": 33, "b": "foo"}) == HookCls(33, "foo")
    assert decoder({"a": 33}) == HookCls(33)

    inspect = at.attrs_classes(verb=IP, typ=HookCls, ctx=Ctx())
    assert inspect(HookCls(33, "foo"))
    assert inspect(HookCls("str", "foo"))
    assert not inspect({"a": 33, "b": "foo"})

    inspect = at.attrs_classes(verb=IJ, typ=HookCls, ctx=Ctx())
    assert inspect({"_type_": "Hook", "a": "str", "b": "foo"})
    assert not inspect({"a": 33, "b": "foo"})
    assert inspect({"_type_": "Hook", "a": 33, "b": "foo"})
    assert inspect({"_type_": "Hook"})


class Ctx2:
    def lookup(self, *, verb, typ, accept_missing=False):
        if typ is None:
            assert accept_missing, "typ is None without accept_missing"
            if verb in JP:
                return str
            else:
                return lambda val: isinstance(val, str)

        if verb in JP:
            return typ
        else:
            return lambda val: isinstance(val, typ)


class Named1(NamedTuple):
    a: int
    b: str = "default"


Named2 = namedtuple("Named2", ["a", "b"])


try:
    Named3 = namedtuple("Named2", ["a", "b"], defaults=["default"])
except TypeError:
    Named3 = None


def test_named_tuples_disregards():
    "Test that named_tuples disregards unknown verbs and types."

    assert at.named_tuples(verb=P2J, typ=int, ctx=Fail()) is None
    assert at.named_tuples(verb=IP, typ=int, ctx=Fail()) is None
    assert at.named_tuples(verb=J2P, typ=tuple, ctx=Fail()) is None
    assert at.named_tuples(verb="dummy", typ=Named1, ctx=Fail()) is None
    assert at.named_tuples(verb="dummy", typ=Named2, ctx=Fail()) is None


@pytest.mark.parametrize("NamedCls,a,has_default", [
    (Named1, 33, True),
    (Named2, "str", False),
    param(Named3, "str", True, marks=skip_if(Named3 is None, "namedtuple does not accept defaults"))
])
def test_named_tuples_encoding(NamedCls, a, has_default):
    "Test that named_tuples encodes and decodes a flat class."

    encoder = at.named_tuples(verb=P2J, typ=NamedCls, ctx=Ctx2())
    assert encoder(NamedCls(a, "foo")) == {"a": a, "b": "foo"}
    assert encoder(NamedCls(a, "default")) == {"a": a} if has_default else {"a": a, "b": "default"}

    decoder = at.named_tuples(verb=J2P, typ=NamedCls, ctx=Ctx2())
    assert decoder({"a": a, "b": "foo"}) == NamedCls(a, "foo")
    assert decoder({"a": a}) == NamedCls(a)

    inspect = at.named_tuples(verb=IP, typ=NamedCls, ctx=Ctx2())
    assert inspect(NamedCls(a, "foo"))
    assert inspect(NamedCls("str", "foo"))
    assert not inspect({"a": a, "b": "foo"})

    inspect = at.named_tuples(verb=IJ, typ=NamedCls, ctx=Ctx2())
    assert not inspect(NamedCls(a, "foo"))
    assert not inspect({"a": None, "b": "foo"})
    assert inspect({"a": a})
    assert inspect({"a": a, "b": "foo"})
    assert not inspect({"b": "foo"})


def test_tuples_disregards():
    "Test that tuples disregards unknown verbs and types."

    assert at.tuples(verb=P2J, typ=Tuple[int, ...], ctx=Fail()) is None
    assert at.tuples(verb=IP, typ=int, ctx=Fail()) is None
    assert at.tuples(verb="dummy", typ=Tuple[int, str], ctx=Fail()) is None


def test_tuples_encoding():
    "Test that tuples encodes and decodes a flat class."

    encoder = at.tuples(verb=P2J, typ=Tuple[int, str], ctx=Ctx2())
    assert encoder((33, "foo")) == [33, "foo"]

    decoder = at.tuples(verb=J2P, typ=Tuple[int, str], ctx=Ctx2())
    assert decoder([33, "foo"]) == (33, "foo")

    inspect = at.tuples(verb=IP, typ=Tuple[int, str], ctx=Ctx2())
    assert inspect((33, "foo"))
    assert not inspect(("str", "foo"))
    assert not inspect((33, "foo", None))

    inspect = at.tuples(verb=IJ, typ=Tuple[int, str], ctx=Ctx2())
    assert inspect([33, "foo"])
    assert not inspect(["str", "foo"])
    assert not inspect([33, "foo", None])
    assert not inspect({})
