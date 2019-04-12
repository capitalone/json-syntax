"""
The JSON syntax library is a combinatorial parser / generator library for managing conversion of Python objects to and
from common JSON types.

It's not strictly limited to JSON, but that's the major use case.
"""

from .ruleset import RuleSet
from .std import (  # noqa
    atoms,
    decimals,
    decimals_as_str,
    floats,
    floats_nan_str,
    iso_dates,
    optional,
    enums,
    faux_enums,
    lists,
    sets,
    dicts,
)
from .attrs import attrs_classes, named_tuples, tuples
from .unions import unions
from .helpers import JSON2PY, PY2JSON, INSP_PY, INSP_JSON, PATTERN  # noqa


def std_ruleset(
    floats=floats,
    decimals=decimals,
    dates=iso_dates,
    enums=enums,
    lists=lists,
    sets=sets,
    unions=unions,
    extras=(),
    custom=RuleSet,
    cache=None,
):
    """
    Constructs a RuleSet with the provided rules. The arguments here are to make it easy to override.

    For example, to replace ``decimals`` with ``decimals_as_str`` just call ``std_ruleset(decimals=decimals_as_str)``
    """
    return custom(
        enums,
        atoms,
        floats,
        decimals,
        dates,
        optional,
        lists,
        attrs_classes,
        sets,
        named_tuples,
        tuples,
        dicts,
        unions,
        *extras,
        cache=cache,
    )
