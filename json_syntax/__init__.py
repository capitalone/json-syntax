"""
The JSON syntax library is a combinatorial parser / generator library for managing conversion of Python objects to and
from common JSON types.

It's not strictly limited to JSON, but that's the major use case.
"""

from .ruleset import RuleSet
from .cache import SimpleCache
from .std import atoms, iso_dates, optional, enums, list_or_tuple, set_or_frozenset
from .attrs import attrs_classes, named_tuples
from .helpers import J2P, P2J  # noqa


def std_ruleset():
    cache = SimpleCache()
    return RuleSet(
        atoms, iso_dates, optional, enums, list_or_tuple, attrs_classes, set_or_frozenset, named_tuples, cache=cache
    )
