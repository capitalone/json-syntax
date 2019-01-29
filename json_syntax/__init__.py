"""
The JSON syntax library is a combinatorial parser / generator library for managing conversion of Python objects to and
from common JSON types.

It's not strictly limited to JSON, but that's the major use case.
"""

from .ruleset import RuleSet
from .cache import SimpleCache
from .std import (  # noqa
    atoms,
    decimals,
    decimals_as_str,
    iso_dates,
    iso_dates_strict,
    optional,
    enums,
    faux_enums,
    lists,
    sets,
    dicts,
)
from .attrs import attrs_classes, named_tuples, tuples
from .unions import unions
from .helpers import J2P, P2J  # noqa


def std_ruleset(
    decimals=decimals,
    dates=iso_dates,
    enums=enums,
    lists=lists,
    sets=sets,
    unions=unions,
):
    """
    Constructs a RuleSet with the provided rules. The arguments here are to make it easy to override.

    For example, to replace ``decimals`` with ``decimals_as_str`` just call ``std_ruleset(decimals=decimals_as_str)``
    """
    return RuleSet(
        atoms,
        decimals,
        dates,
        optional,
        enums,
        lists,
        attrs_classes,
        sets,
        dicts,
        named_tuples,
        tuples,
        unions,
        cache=SimpleCache(),
    )
