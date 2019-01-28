from dataclasses import dataclass
from datetime import date
from typing import Optional, List
import json_syntax as js


@dataclass
class CompositeThing:
    foo: bool
    bar: List['Other']
    qux: Optional[int]


@dataclass
class Other:
    x: float
    y: date
    z: Optional[CompositeThing]


def test_encoding_of_composite_thing():
    "We should get an encoded composite thing."
    rs = js.std_ruleset()
    encoder = rs.lookup(typ=CompositeThing, verb=js.P2J)

    instance = CompositeThing(
        foo=False, bar=[
            Other(x=3.3, y=date(1944, 4, 4), z=None),
            Other(x=4.4, y=date(1955, 5, 5), z=None)],
        qux=77
    )
    print(encoder)
    assert encoder(instance) == {
        'foo': False,
        'bar': [
            {'x': 3.3,
             'y': '1944-04-04',
             'z': None},
            {'x': 4.4,
             'y': '1955-05-05',
             'z': None},
        ], 'qux': 77
    }


def test_decoding_of_composite_thing():
    "We should get an encoded composite thing."
    rs = js.std_ruleset()
    decoder = rs.lookup(typ=CompositeThing, verb=js.J2P)

    blob = {
        'foo': False,
        'bar': [
            {'x': 3.3,
             'y': '1944-04-04',
             'z': None},
            {'x': 4.4,
             'y': '1955-05-05',
             'z': None},
        ], 'qux': 77
    }

    print(decoder)
    assert decoder(blob) == CompositeThing(
        foo=False, bar=[
            Other(x=3.3, y=date(1944, 4, 4), z=None),
            Other(x=4.4, y=date(1955, 5, 5), z=None)
        ], qux=77
    )
