import pytest

from datetime import date
from decimal import Decimal
import json_syntax as syn

try:
    from tests.types_std_ann import things, accounts
except SyntaxError:
    from tests.types_std_noann import things, accounts


@pytest.mark.parametrize("Thing,Other", things)
def test_encoding_of_composite_thing(Thing, Other):
    "Test encoding of a cyclic type."
    rs = syn.std_ruleset()
    encoder = rs.lookup(typ=Thing, verb=syn.PY2JSON)
    decoder = rs.lookup(typ=Thing, verb=syn.JSON2PY)

    def pythonic():
        return Thing(
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


@pytest.mark.parametrize("Account,TransType,Trans", accounts)
def test_readme_example(Account, TransType, Trans):
    "Test encoding the readme example."
    rules = syn.std_ruleset()
    encode_account = rules.lookup(typ=Account, verb=syn.PY2JSON)
    decode_account = rules.lookup(typ=Account, verb=syn.JSON2PY)

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
