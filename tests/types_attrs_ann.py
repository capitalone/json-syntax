import attr
from typing import NamedTuple

from tests.types_attrs_noann import flat_types, Hooks, hook_types

try:
    from dataclasses import dataclass
except ImportError:
    dataclass = None


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
