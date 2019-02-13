import attr
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, List


@attr.s
class CompositeThing:
    foo = attr.ib(type=bool)
    bar = attr.ib(type=List["Other"])
    qux = attr.ib(type=Optional[int])


@attr.s
class Other:
    x = attr.ib(type=float)
    y = attr.ib(type=date)
    z = attr.ib(type=Optional[CompositeThing])


things = [(CompositeThing, Other)]


@attr.s
class Account:
    user = attr.ib(type=str)
    transactions = attr.ib(type=List["Trans"])
    balance = attr.ib(Decimal(0), type=Decimal)


class TransType(Enum):
    withdraw = 0
    deposit = 1


@attr.s
class Trans:
    type = attr.ib(type=TransType)
    amount = attr.ib(type=Decimal)
    stamp = attr.ib(type=date)


accounts = [(Account, TransType, Trans)]
