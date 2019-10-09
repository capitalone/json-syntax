try:
    from dataclasses import dataclass
except ImportError:
    from attr import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, List


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


things = [(CompositeThing, Other)]


@dataclass
class Account:
    user: str
    transactions: List["Trans"]
    balance: Decimal = Decimal(0)


class TransType(Enum):
    withdraw = 0
    deposit = 1


@dataclass
class Trans:
    type: TransType
    amount: Decimal
    stamp: date


accounts = [(Account, TransType, Trans)]
