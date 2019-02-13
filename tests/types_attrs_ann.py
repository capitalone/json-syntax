import attr
from collections import namedtuple
try:
    from dataclasses import dataclass
except ImportError:
    dataclass = None

from tests.types_attrs_noann import flat_types, hook_type, Hooks


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
