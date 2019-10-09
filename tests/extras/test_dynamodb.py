import pytest

from json_syntax.extras.dynamodb import dynamodb_ruleset
from json_syntax.helpers import NoneType

from fractions import Fraction
from decimal import Decimal
from typing import List, Set, Optional

try:
    import attr
except ImportError:
    attr = None


def encode(value, typ):
    return dynamodb_ruleset().python_to_dynamodb(typ)(value)


def decode(value, typ):
    return dynamodb_ruleset().dynamodb_to_python(typ)(value)


def test_optional():
    assert encode(None, Optional[int]) == {"NULL": True}
    assert encode(5, Optional[int]) == {"N": "5"}
    assert decode({"NULL": True}, Optional[str]) is None
    assert decode({"S": "wat"}, Optional[str]) == "wat"


def test_bool():
    assert encode(True, bool) == {"BOOL": True}
    assert decode({"BOOL": False}, bool) is False


def test_binary():
    assert encode(b"foobar", bytes) == {"B": "Zm9vYmFy"}
    assert decode({"B": "Zm9vYmFy"}, bytes) == b"foobar"


def test_number1():
    assert encode(55.125, float) == {"N": "55.125"}
    assert decode({"N": "-55.125"}, float) == -55.125


def test_number2():
    with pytest.raises(ValueError):
        encode(float("nan"), float)


def test_number3():
    assert encode(Fraction(441, 8), Fraction) == {"N": "55.125"}
    assert decode({"N": "55.125"}, Fraction) == Fraction(441, 8)


def test_number4():
    assert encode(Decimal("55.125"), Decimal) == {"N": "55.125"}
    assert decode({"N": "-55.125"}, Decimal) == Decimal("-55.125")


def test_string():
    assert encode("foobar", str) == {"S": "foobar"}
    assert decode({"S": "foobar"}, str) == "foobar"


def test_list():
    assert encode([1, 2, 4, 5], List[int]) == {
        "L": [{"N": str(x)} for x in [1, 2, 4, 5]]
    }
    assert decode({"L": [{"S": "apple"}, {"S": "banana"}]}, List[str]) == [
        "apple",
        "banana",
    ]


def cheat(value):
    for val in value.values():
        val.sort()
    return value


def test_str_set():
    assert cheat(encode({"foo", "bar", "qux"}, Set[str])) == {
        "SS": ["bar", "foo", "qux"]
    }
    assert decode({"SS": ["foo", "bar", "qux"]}, Set[str]) == {"foo", "bar", "qux"}


def test_num_set():
    assert cheat(encode({-33.5, 11.25, 1.75}, Set[float])) == {
        "NS": ["-33.5", "1.75", "11.25"]
    }
    assert decode({"NS": [11.25, 1.75, -33.5]}, Set[float]) == {-33.5, 11.25, 1.75}


def test_bin_set():
    assert cheat(encode({b"foo", b"bar", b"qux"}, Set[bytes])) == {
        "BS": ["YmFy", "Zm9v", "cXV4"]
    }
    assert decode({"BS": ["YmFy", "Zm9v", "cXV4"]}, Set[bytes]) == {
        b"foo",
        b"bar",
        b"qux",
    }


@attr.s
class Inner:
    name = attr.ib(type=str)


@attr.s
class Outer:
    stuff = attr.ib(type=Inner)
    count = attr.ib(type=int, default=7)


def test_map1():
    subj = Outer(count=3, stuff=Inner(name="bob"))
    expected = {"M": {"count": {"N": "3"}, "stuff": {"M": {"name": {"S": "bob"}}}}}
    assert encode(subj, Outer) == expected

    subj = {"M": {"count": {"N": "3"}, "stuff": {"M": {"name": {"S": "bob"}}}}}
    expected = Outer(count=3, stuff=Inner(name="bob"))
    assert decode(subj, Outer) == expected


def test_map2():
    subj = Outer(stuff=Inner(name="bob"))
    expected = {"M": {"stuff": {"M": {"name": {"S": "bob"}}}}}
    assert encode(subj, Outer) == expected

    subj = {
        "M": {"stuff": {"M": {"name": {"S": "bob"}}}, "other_key": {"S": "ignored"}}
    }
    expected = Outer(stuff=Inner(name="bob"))
    assert decode(subj, Outer) == expected
