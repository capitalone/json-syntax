import pytest

import attr
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from itertools import product
from typing import Union, List, Tuple, Set, FrozenSet, Dict

from json_syntax import std_ruleset
from json_syntax.helpers import P2J, J2P, IP, IJ, NoneType


@attr.s(frozen=True)
class Point:
    x = attr.ib(type=float)
    y = attr.ib(0.0, type=float)


class Dir(Enum):
    UP = 1
    DOWN = 2


cases = [
    (NoneType, None, None),
    (bool, True, True),
    (int, 5, 5),
    (float, 3.3, 3.3),
    (Decimal, Decimal("5.5"), Decimal("5.5")),
    (str, "str", "str"),
    (date, date(2010, 10, 10), "2010-10-10"),
    (datetime, datetime(2011, 11, 11, 11, 11, 11), "2011-11-11T11:11:11"),
    (Point, Point(x=4.5, y=6.6), {"x": 4.5, "y": 6.6}),
    (Dir, Dir.UP, "UP"),
    (List[Point], [Point(x=4.5, y=6.6)], [{"x": 4.5, "y": 6.6}]),
    (Tuple[Point, ...], (Point(x=4.5, y=6.6),), [{"x": 4.5, "y": 6.6}]),
    (Set[Point], {Point(x=4.5, y=6.6)}, [{"x": 4.5, "y": 6.6}]),
    (FrozenSet[Point], frozenset([Point(x=4.5, y=6.6)]), [{"x": 4.5, "y": 6.6}]),
    (Dict[Dir, Decimal], {Dir.UP: Decimal("7.7")}, {"UP": Decimal("7.7")}),
    (Dict[str, float], {"a": 2.3, "b": 3.4}, {"a": 2.3, "b": 3.4}),
]


@pytest.mark.parametrize("typ,py,js", cases)
def test_simple(typ, py, js):
    rs = std_ruleset()
    act = rs.lookup(verb=P2J, typ=typ)
    assert act(py) == js
    act = rs.lookup(verb=J2P, typ=typ)
    assert act(js) == py


def ambiguous(left, right):
    if left == str and right in {Dir, date, datetime}:
        return "str prevents {} matching".format(right)
    if left == date and right == datetime:
        return "supertype date prevents subtype datetime matching"
    if left == datetime and right == date:
        return "dates in iso format are valid datetimes"
    if left == Dict[str, float] and right == Point:
        # Note that this is the case where the attrs class has homogenous fields
        return "dict prevents attrs class matching"
    ambiguous = {List[Point], Tuple[Point, ...], Set[Point], FrozenSet[Point]}
    if left in ambiguous and right in ambiguous:
        return "collections are all represented as json arrays"
    return


def cvt_map():
    for left, right in product(cases, cases):
        if left is right:
            continue
        left_type, left_python, left_json = left
        right_type, right_python, right_json = right

        if (
            left_json == right_json
            or left_python == right_python
            or ambiguous(left_type, right_type)
        ):
            continue

        typ = Union[left_type, right_type]
        yield (P2J, typ, left_python, left_json)
        yield (P2J, typ, right_python, right_json)
        yield (J2P, typ, left_json, left_python)
        yield (J2P, typ, right_json, right_python)


@pytest.mark.parametrize("verb,typ,subj,expect", cvt_map())
def test_convert_unions(verb, typ, subj, expect):
    "Test that the unions rule is able to convert possible types."

    action = std_ruleset().lookup(verb=verb, typ=typ)

    assert action(subj) == expect


def check_map():
    for left, right in product(cases, cases):
        if left is right:
            continue
        left_type, left_python, left_json = left
        right_type, right_python, right_json = right

        if (
            left_json == right_json
            or left_python == right_python
            or ambiguous(left_type, right_type)
        ):
            continue

        typ = Union[left_type, right_type]
        yield (IP, typ, left_python)
        yield (IP, typ, right_python)
        yield (IJ, typ, left_json)
        yield (IJ, typ, right_json)


@pytest.mark.parametrize("verb,typ,subj", check_map())
def test_check_unions(verb, typ, subj):
    "Test that the unions rule is able to verify possible types."

    action = std_ruleset().lookup(verb=verb, typ=typ)

    assert action(subj)
