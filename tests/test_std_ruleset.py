from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, List
import json_syntax as syn


@dataclass
class CompositeThing:
    foo: bool
    bar: List["Other"]
    qux: Optional[int]


@dataclass
class Other:
    x: float
    y: date
    z: Optional[CompositeThing]


def test_encoding_of_composite_thing():
    "Test encoding of a cyclic type."
    rs = syn.std_ruleset()
    encoder = rs.lookup(typ=CompositeThing, verb=syn.P2J)
    decoder = rs.lookup(typ=CompositeThing, verb=syn.J2P)

    def pythonic():
        return CompositeThing(
            foo=False,
            bar=[
                Other(x=3.3, y=date(1944, 4, 4), z=None),
                Other(x=4.4, y=date(1955, 5, 5), z=None),
            ],
            qux=77,
        )

    def jsonic():
        return {
            "foo": False,
            "bar": [
                {"x": 3.3, "y": "1944-04-04", "z": None},
                {"x": 4.4, "y": "1955-05-05", "z": None},
            ],
            "qux": 77,
        }

    assert encoder(pythonic()) == jsonic()
    assert decoder(jsonic()) == pythonic()


@dataclass
class Account:
    user: str
    transactions: List["Trans"]
    balance: Decimal = 0


class TransType(Enum):
    withdraw = 0
    deposit = 1


@dataclass
class Trans:
    type: TransType
    amount: Decimal
    stamp: date


def test_readme_example():
    "Test encoding the readme example."
    rules = syn.std_ruleset()
    encode_account = rules.lookup(typ=Account, verb=syn.P2J)
    decode_account = rules.lookup(typ=Account, verb=syn.J2P)

    def pythonic():
        return Account(
            "bob",
            [Trans(TransType.withdraw, Decimal("523.33"), date(2019, 4, 4))],
            Decimal("77.00"),
        )

    def jsonic():
        return {
            "user": "bob",
            "transactions": [
                {"type": "withdraw", "amount": Decimal("523.33"), "stamp": "2019-04-04"}
            ],
            "balance": Decimal("77.00"),
        }

    assert encode_account(pythonic()) == jsonic()
    assert decode_account(jsonic()) == pythonic()
