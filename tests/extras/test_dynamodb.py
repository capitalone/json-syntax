import pytest

from json_syntax.extras.dynamodb import dynamodb_ruleset
from json_syntax.helpers import NoneType

from fractions import Fraction
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

try:
    import attr
except ImportError:
    attr = None


def encode(value, typ):
    return dynamodb_ruleset().python_to_dynamodb(typ)(value)


def decode(value, typ):
    return dynamodb_ruleset().dynamodb_to_python(typ)(value)


def encode_item(value, typ):
    return dynamodb_ruleset().python_to_ddb_item(typ)(value)


def decode_item(value, typ):
    return dynamodb_ruleset().ddb_item_to_python(typ)(value)


def test_optional():
    assert encode(None, Optional[int]) == {"NULL": True}
    assert encode(5, Optional[int]) == {"N": "5"}
    assert decode({"NULL": True}, Optional[str]) is None
    assert decode({"S": "wat"}, Optional[str]) == "wat"


def test_null():
    assert encode(None, type(None)) == {"NULL": True}
    assert decode({"NULL": True}, type(None)) is None


def test_bool():
    assert encode(True, bool) == {"BOOL": True}
    assert decode({"BOOL": False}, bool) is False


def test_binary():
    assert encode(b"foobar", bytes) == {"B": "Zm9vYmFy"}
    assert decode({"B": "Zm9vYmFy"}, bytes) == b"foobar"
    assert decode({"B": b"Zm9vYmFy"}, bytes) == b"foobar"


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


def test_dict():
    assert encode({"A": 1, "B": 2}, Dict[str, int]) == {
        "M": {"A": {"N": "1"}, "B": {"N": "2"}}
    }
    assert decode({"M": {"A": {"N": "1"}, "B": {"N": "2"}}}, Dict[str, int]) == {
        "A": 1,
        "B": 2,
    }


def cheat(value):
    if isinstance(value, dict):
        for key, val in value.items():
            if key in ('SS', 'NS', 'BS'):
                val.sort()
            else:
                cheat(val)
    elif isinstance(value, list):
        for val in value:
            cheat(val)
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
    assert decode({"BS": [b"YmFy", b"Zm9v", b"cXV4"]}, Set[bytes]) == {
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


def test_item1():
    subj = Outer(count=3, stuff=Inner(name="bob"))
    expected = {"count": {"N": "3"}, "stuff": {"M": {"name": {"S": "bob"}}}}
    assert encode_item(subj, Outer) == expected

    subj = {"count": {"N": "3"}, "stuff": {"M": {"name": {"S": "bob"}}}}
    expected = Outer(count=3, stuff=Inner(name="bob"))
    assert decode_item(subj, Outer) == expected


def test_item2():
    subj = Outer(stuff=Inner(name="bob"))
    expected = {"stuff": {"M": {"name": {"S": "bob"}}}}
    assert encode_item(subj, Outer) == expected

    subj = {"stuff": {"M": {"name": {"S": "bob"}}}, "other_key": {"S": "ignored"}}
    expected = Outer(stuff=Inner(name="bob"))
    assert decode_item(subj, Outer) == expected


def test_ad_hoc_atoms():
    rs = dynamodb_ruleset()
    actual = rs.ad_hoc(
        ':',
        arg_null=None,
        arg_bool=False,
        arg_int=3,
        arg_float=6.6,
        arg_dec=Decimal('-7.888'),
        arg_str='some_string',
        arg_bytes=b'some_byes',
        arg_class=Outer(stuff=Inner(name="bob")),
    )
    assert actual == {
        ':arg_bool': {'BOOL': False},
        ':arg_bytes': {'B': 'c29tZV9ieWVz'},
        ':arg_dec': {'N': '-7.888'},
        ':arg_float': {'N': '6.6'},
        ':arg_int': {'N': '3'},
        ':arg_null': {'NULL': True},
        ':arg_str': {'S': 'some_string'},
        ':arg_class': {'M': {'stuff': {'M': {'name': {'S': 'bob'}}}}},
    }


def test_ad_hoc_typed():
    rs = dynamodb_ruleset()
    actual = rs.ad_hoc(
        ':',
        arg_opt1=(None, Optional[int]),
        arg_opt2=(5, Optional[int]),
        arg_list=([3, 2.2, 6.0], List[float]),
        arg_tup=((3, 2.2, 6.0), Tuple[float, ...]),
        arg_class=(Outer(stuff=Inner(name="bob")), Outer),
        arg_str_set=({'foo', 'bar', 'qux'}, Set[str])
    )
    assert cheat(actual) == {
        ':arg_opt1': {'NULL': True},
        ':arg_opt2': {'N': '5'},
        ':arg_list': {'L': [{'N': '3'}, {'N': '2.2'}, {'N': '6.0'}]},
        ':arg_tup': {'L': [{'N': '3'}, {'N': '2.2'}, {'N': '6.0'}]},
        ':arg_class': {'M': {'stuff': {'M': {'name': {'S': 'bob'}}}}},
        ':arg_str_set': {'SS': ['bar', 'foo', 'qux']},
    }
