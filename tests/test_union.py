import pytest

import attr
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from itertools import product
from typing import Union, List, Tuple, Set, FrozenSet, Dict

from json_syntax import std_ruleset
from json_syntax.helpers import PY2JSON, JSON2PY, INSP_PY, INSP_JSON, NoneType


@attr.s(frozen=True)
class Point:
    x = attr.ib(type=float)
    y = attr.ib(0.0, type=float)


class Dir(Enum):
    UP = 1
    DOWN = 2


atoms = [(NoneType, None, None), (bool, True, True)]

nums = [(int, 5, 5), (float, 3.3, 3.3), (Decimal, Decimal("5.5"), Decimal("5.5"))]

strings = [
    (str, "str", "str"),
    (date, date(2010, 10, 10), "2010-10-10"),
    (datetime, datetime(2011, 11, 11, 11, 11, 11), "2011-11-11T11:11:11"),
    (Dir, Dir.UP, "UP"),
]

arrays = [
    (List[Point], [Point(x=4.5, y=6.6)], [{"x": 4.5, "y": 6.6}]),
    (Tuple[Point, ...], (Point(x=4.5, y=6.6),), [{"x": 4.5, "y": 6.6}]),
    (Set[Point], {Point(x=4.5, y=6.6)}, [{"x": 4.5, "y": 6.6}]),
    (FrozenSet[Point], frozenset([Point(x=4.5, y=6.6)]), [{"x": 4.5, "y": 6.6}]),
]

dicts = [
    (Point, Point(x=4.5, y=6.6), {"x": 4.5, "y": 6.6}),
    (Dict[Dir, Decimal], {Dir.UP: Decimal("7.7")}, {"UP": Decimal("7.7")}),
    (Dict[str, float], {"a": 2.3, "b": 3.4}, {"a": 2.3, "b": 3.4}),
]

cats = [atoms, nums, strings, arrays, dicts]


@pytest.mark.parametrize("typ,py,js", [trip for cat in cats for trip in cat])
def test_simple(typ, py, js):
    rs = std_ruleset()
    act = rs.lookup(verb=PY2JSON, typ=typ)
    assert act(py) == js
    act = rs.lookup(verb=JSON2PY, typ=typ)
    assert act(js) == py


def _pairs():
    for i in range(0, len(cats)):
        lefts = cats[i]
        rights = cats[(i + 2) % len(cats)]
        yield from product(lefts, rights)


def cvt_map():
    for left, right in _pairs():
        left_type, left_python, left_json = left
        right_type, right_python, right_json = right

        typ = Union[left_type, right_type]
        yield (PY2JSON, typ, left_python, left_json)
        yield (PY2JSON, typ, right_python, right_json)
        yield (JSON2PY, typ, left_json, left_python)
        yield (JSON2PY, typ, right_json, right_python)


@pytest.mark.parametrize("verb,typ,subj,expect", cvt_map())
def test_convert_unions(verb, typ, subj, expect):
    "Test that the unions rule is able to convert possible types."

    action = std_ruleset().lookup(verb=verb, typ=typ)

    assert action(subj) == expect


def check_map():
    for left, right in _pairs():
        left_type, left_python, left_json = left
        right_type, right_python, right_json = right

        typ = Union[left_type, right_type]
        yield (INSP_PY, typ, left_python)
        yield (INSP_PY, typ, right_python)
        yield (INSP_JSON, typ, left_json)
        yield (INSP_JSON, typ, right_json)


@pytest.mark.parametrize("verb,typ,subj", check_map())
def test_check_unions(verb, typ, subj):
    "Test that the unions rule is able to verify possible types."

    action = std_ruleset().lookup(verb=verb, typ=typ)

    assert action(subj)
