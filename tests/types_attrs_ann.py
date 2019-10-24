import attr
from typing import NamedTuple

from tests.types_attrs_noann import (  # noqa
    flat_types,
    hook_types,
    Hooks,
    Dict1,
    Named1,
    Named2,
)

try:
    from dataclasses import dataclass
except ImportError:
    dataclass = None

try:
    from typing import TypedDict
except ImportError:
    TypedDict = None


@attr.s(auto_attribs=True)
class Flat2:
    a: int
    b: str = "default"


flat_types.append(Flat2)
if dataclass:

    @dataclass
    class Flat3:
        a: int
        b: str = "default"

    flat_types.append(Flat3)


@attr.s(auto_attribs=True)
class Hook2(Hooks):
    a: int
    b: str = "default"


hook_types.append(Hook2)
if dataclass:

    @dataclass
    class Hook3(Hooks):
        a: int
        b: str = "default"

    hook_types.append(Hook3)


class Named3(NamedTuple):
    a: int
    b: str = "default"


Dict2 = None
if TypedDict:

    class Dict2(TypedDict):
        a: int
        b: str
