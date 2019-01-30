import pytest
from unittest.mock import Mock

from json_syntax import attrs as at
from json_syntax.helpers import J2P, P2J, IP, IJ, JPI, JP, II

import attr
from collections import namedtuple
from dataclasses import dataclass
from typing import NamedTuple, Tuple


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


@attr.s(auto_attribs=True)
class Flat1:
    a: int
    b: str = "default"


@dataclass
class Flat2:
    a: int
    b: str = "default"


def test_attrs_classes_disregards():
    "Test that attrs_classes disregards unknown verbs and types."

    assert at.attrs_classes(verb=P2J, typ=int, ctx=Fail()) is None
    assert at.attrs_classes(verb=IP, typ=int, ctx=Fail()) is None
    assert at.attrs_classes(verb=J2P, typ=object, ctx=Fail()) is None
    assert at.attrs_classes(verb="dummy", typ=Flat1, ctx=Fail()) is None
    assert at.attrs_classes(verb="dummy", typ=Flat2, ctx=Fail()) is None


@pytest.mark.parametrize("FlatCls", [Flat1, Flat2])
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


class Hooks:
    @classmethod
    def __json_pre_init__(cls, value):
        if isinstance(value, list):
            value = {"a": value[0], "b": value[1]}
        return value

    @classmethod
    def __json_check__(cls, value):
        return value.get("_type_") == "Hook"

    def __json_post_encode__(cls, value):
        return dict(value, _type_="Hook")


@attr.s(auto_attribs=True)
class Hook1(Hooks):
    a: int
    b: str = "default"


@dataclass
class Hook2(Hooks):
    a: int
    b: str = "default"


@pytest.mark.parametrize("HookCls", [Hook1, Hook2])
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


Named2 = namedtuple("Named2", ["a", "b"], defaults=["default"])


def test_named_tuples_disregards():
    "Test that named_tuples disregards unknown verbs and types."

    assert at.named_tuples(verb=P2J, typ=int, ctx=Fail()) is None
    assert at.named_tuples(verb=IP, typ=int, ctx=Fail()) is None
    assert at.named_tuples(verb=J2P, typ=tuple, ctx=Fail()) is None
    assert at.named_tuples(verb="dummy", typ=Named1, ctx=Fail()) is None
    assert at.named_tuples(verb="dummy", typ=Named2, ctx=Fail()) is None


@pytest.mark.parametrize("NamedCls,a", [(Named1, 33), (Named2, "str")])
def test_named_tuples_encoding(NamedCls, a):
    "Test that named_tuples encodes and decodes a flat class."

    encoder = at.named_tuples(verb=P2J, typ=NamedCls, ctx=Ctx2())
    assert encoder(NamedCls(a, "foo")) == {"a": a, "b": "foo"}
    assert encoder(NamedCls(a, "default")) == {"a": a}

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
