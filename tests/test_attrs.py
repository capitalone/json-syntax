import pytest
from unittest.mock import Mock

from json_syntax import attrs as at
from json_syntax.helpers import JSON2PY, PY2JSON, INSP_PY, INSP_JSON

import attr
from collections import namedtuple

try:
    from dataclasses import dataclass
except ImportError:
    dataclass = lambda cls: None
from typing import NamedTuple, Tuple

try:
    from tests.types_attrs_ann import flat_types, hook_types, Named1, Named2, Named3
except SyntaxError:
    from tests.types_attrs_noann import flat_types, hook_types, Named1, Named2, Named3


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
    assert at.attrs_classes(verb="dummy", typ=flat_types[0], ctx=Fail()) is None


@pytest.mark.parametrize("FlatCls", flat_types)
def test_attrs_encoding(FlatCls):
    "Test that attrs_classes encodes and decodes a flat class."

    encoder = at.attrs_classes(verb=PY2JSON, typ=FlatCls, ctx=Ctx())
    assert encoder(FlatCls(33, "foo")) == {"a": 33, "b": "foo"}
    assert encoder(FlatCls(33, "default")) == {"a": 33}

    decoder = at.attrs_classes(verb=JSON2PY, typ=FlatCls, ctx=Ctx())
    assert decoder({"a": 33, "b": "foo"}) == FlatCls(33, "foo")
    assert decoder({"a": 33}) == FlatCls(33)

    inspect = at.attrs_classes(verb=INSP_PY, typ=FlatCls, ctx=Ctx())
    assert inspect(FlatCls(33, "foo"))
    assert inspect(FlatCls("str", "foo"))
    assert not inspect({"a": 33, "b": "foo"})

    inspect = at.attrs_classes(verb=INSP_JSON, typ=FlatCls, ctx=Ctx())
    assert not inspect(FlatCls(33, "foo"))
    assert not inspect({"a": "str", "b": "foo"})
    assert inspect({"a": 33})
    assert inspect({"a": 33, "b": "foo"})
    assert not inspect({"b": "foo"})


@pytest.mark.parametrize("HookCls", hook_types)
def test_attrs_hooks(HookCls):
    "Test that attrs_classes enables hooks."

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
