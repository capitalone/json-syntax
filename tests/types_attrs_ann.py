import attr

from .common import dataclasses as dc, typing as t
from .types_attrs_common import Hooks, T, U


@attr.s(auto_attribs=True)
class Flat:
    a: int
    b: str = "default"


@attr.s(auto_attribs=True)
class GenFlat(t.Generic[T]):
    a: T
    b: str = "default"


@attr.s(auto_attribs=True)
class Hook(Hooks):
    a: int
    b: str = "default"


class Named(t.NamedTuple):
    a: int
    b: str = "default"


class Dict(t.TypedDict):
    a: int
    b: str


@attr.s(auto_attribs=True, slots=True)
class GenExample(t.Generic[T, U]):
    body: T
    count: int
    messages: t.List[U]


if dc.dataclass:

    @dc.dataclass
    class FlatDc:
        a: int
        b: str = "default"

    @dc.dataclass
    class GenFlatDc(t.Generic[T]):
        a: T
        b: str = "default"

    @dc.dataclass
    class HookDc(Hooks):
        a: int
        b: str = "default"

    @dc.dataclass
    class GenExampleDc(t.Generic[T, U]):
        body: T
        count: int
        messages: t.List[U]


else:
    FlatDc = GenFlatDc = HookDc = GenericExampleDc = None
