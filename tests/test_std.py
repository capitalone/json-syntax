from json_syntax import std
from json_syntax.helpers import J2P, P2J

from datetime import datetime, date
from enum import Enum, IntEnum
import typing


class Dummy:
    "A dummy context that blows up when it shouldn't be called."
    def lookup_inner(self, *, verb, typ):
        raise AssertionError("Unexpected in this test.")


Mystery = typing.Tuple['Mystery', 'Thing']


def test_atoms_disregard():
    "Test the atoms rule will disregard unknown types and verbs."

    assert std.atoms(verb="unknown", typ=str, ctx=Dummy()) is None
    assert std.atoms(verb=J2P, typ=Mystery, ctx=Dummy()) is None
    assert std.atoms(verb=P2J, typ=Mystery, ctx=Dummy()) is None


def test_atoms_str():
    "Test the atoms rule will generate encoders and decoders for strings."

    decoder = std.atoms(verb=J2P, typ=str, ctx=Dummy())
    assert decoder("some string") == "some string"

    encoder = std.atoms(verb=P2J, typ=str, ctx=Dummy())
    assert encoder("some string") == "some string"


def test_atoms_int():
    "Test the atoms rule will generate encoders and decoders for integers."

    decoder = std.atoms(verb=J2P, typ=int, ctx=Dummy())
    assert decoder(77) == 77

    encoder = std.atoms(verb=P2J, typ=int, ctx=Dummy())
    assert encoder(77) == 77


def test_atoms_bool():
    "Test the atoms rule will generate encoders and decoders for booleans."

    decoder = std.atoms(verb=J2P, typ=bool, ctx=Dummy())
    assert decoder(False) is False
    assert decoder(True) is True

    encoder = std.atoms(verb=P2J, typ=bool, ctx=Dummy())
    assert encoder(False) is False
    assert encoder(True) is True


def test_atoms_float():
    "Test the atoms rule will generate encoders and decoders for floats that are tolerant of integers."

    decoder = std.atoms(verb=J2P, typ=float, ctx=Dummy())
    assert decoder(77.7) == 77.7
    assert decoder(77) == 77.0

    encoder = std.atoms(verb=P2J, typ=float, ctx=Dummy())
    assert encoder(77.7) == 77.7


def test_atoms_null():
    "Test the atoms rule will generate encoders and decoders for None / null."

    decoder = std.atoms(verb=J2P, typ=type(None), ctx=Dummy())
    assert decoder(None) is None

    encoder = std.atoms(verb=P2J, typ=type(None), ctx=Dummy())
    assert encoder(None) is None


def test_iso_dates_disregard():
    "Test the iso_dates rule will disregard unknown types and verbs."

    assert std.iso_dates(verb="unknown", typ=date, ctx=Dummy()) is None
    assert std.iso_dates(verb=J2P, typ=Mystery, ctx=Dummy()) is None
    assert std.iso_dates(verb=P2J, typ=Mystery, ctx=Dummy()) is None


def test_iso_dates():
    "Test the iso_dates rule will generate encoders and decoders for dates using ISO8601, accepting datetimes as input."

    decoder = std.iso_dates(verb=J2P, typ=date, ctx=Dummy())
    assert decoder('1776-07-04') == date(1776, 7, 4)
    assert decoder('6543-02-01T09:09:09') == date(6543, 2, 1)

    encoder = std.iso_dates(verb=P2J, typ=date, ctx=Dummy())
    assert encoder(date(1776, 7, 4)) == '1776-07-04'


def test_iso_dates_strict():
    "Test the iso_dates_strict rule will generate encoders and decoders for dates using ISO8601, rejecting datetimes as input to dates."

    decoder = std.iso_dates(verb=J2P, typ=date, ctx=Dummy())
    assert decoder('1776-07-04') == date(1776, 7, 4)
    assert decoder('6543-02-01T09:09:09') == date(6543, 2, 1)

    encoder = std.iso_dates(verb=P2J, typ=date, ctx=Dummy())
    assert encoder(date(1776, 7, 4)) == '1776-07-04'


def test_iso_datetimes():
    "Test the iso_dates rule will generate encoders and decoders for datetimes using ISO8601."

    decoder = std.iso_dates(verb=J2P, typ=datetime, ctx=Dummy())
    assert decoder('6666-06-06T12:12:12.987654') == datetime(6666, 6, 6, 12, 12, 12, 987654)

    encoder = std.iso_dates(verb=P2J, typ=datetime, ctx=Dummy())
    assert encoder(datetime(6666, 6, 6, 12, 12, 12, 987654)) == '6666-06-06T12:12:12.987654'


class Enum1(Enum):
    ABLE = 'a'
    BAKER = 'b'
    CHARLIE = 'c'


def test_enums_disregard():
    "Test the iso_dates rule will disregard unknown types and verbs."

    assert std.enums(verb="unknown", typ=Enum1, ctx=Dummy()) is None
    assert std.enums(verb=J2P, typ=Mystery, ctx=Dummy()) is None
    assert std.enums(verb=P2J, typ=Mystery, ctx=Dummy()) is None


def test_enums():
    "Test the enums rule will generate encoders and decoders for enumerated types."

    decoder = std.enums(verb=J2P, typ=Enum1, ctx=Dummy())
    assert decoder('ABLE') == Enum1.ABLE
    assert decoder('CHARLIE') == Enum1.CHARLIE

    encoder = std.enums(verb=P2J, typ=Enum1, ctx=Dummy())
    assert encoder(Enum1.BAKER) == 'BAKER'
    assert encoder(Enum1.CHARLIE) == 'CHARLIE'


class Enum2(IntEnum):
    ALPHA = 1
    BETA = 2
    GAMMA = 3


def test_enums_int():
    "Test the enums rule will generate encoders and decoders for enumerated type subclasses."
    decoder = std.enums(verb=J2P, typ=Enum2, ctx=Dummy())
    assert decoder('ALPHA') == Enum2.ALPHA
    assert decoder('GAMMA') == Enum2.GAMMA

    encoder = std.enums(verb=P2J, typ=Enum2, ctx=Dummy())
    assert encoder(Enum2.BETA) == 'BETA'
    assert encoder(Enum2.GAMMA) == 'GAMMA'
