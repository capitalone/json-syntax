from .helpers import has_origin, issub_safe, NoneType, JP, J2P, P2J, IJ, IP, II, JPI
from .convert import (
    convert_none,
    convert_date_loosely,
    convert_enum_str,
    convert_str_enum,
    convert_optional,
    check_optional,
    convert_collection,
    check_collection,
    convert_mapping,
    check_mapping,
    check_float,
    check_isinst,
    check_value_error,
)

from collections import OrderedDict
from datetime import datetime, date
from enum import Enum
from functools import partial
from operator import contains
from typing import Union

"""
These are standard rules to handle various types.

All rules take a verb, a Python type and a context, which is generally a RuleSet. A rule returns a conversion function
for that verb.
"""


def atoms(*, verb, typ, ctx):
    "Rule to handle atoms on both sides."
    if issub_safe(typ, (str, float, int, NoneType)):
        if verb in JP:
            if typ is NoneType:
                return convert_none
            for base in (str, float, bool, int):
                if issubclass(typ, base):
                    return base
        elif verb == IP:
            for base in (NoneType, str, float, bool, int):
                if issubclass(typ, base):
                    return partial(check_isinst, typ=base)
        elif verb == IJ:
            if issubclass(typ, float):
                return check_float
            for base in (NoneType, str, bool, int):
                if issubclass(typ, base):
                    return partial(check_isinst, typ=base)


def iso_dates(*, verb, typ, ctx, loose_json=True):
    "Rule to handle iso formatted datetimes and dates."
    if issub_safe(typ, date):
        if verb == P2J:
            if issubclass(typ, datetime):
                return datetime.isoformat
            return date.isoformat
        elif verb == J2P:
            if issubclass(typ, datetime):
                return datetime.fromisoformat
            return convert_date_loosely if loose_json else date.fromisoformat
        elif verb == IP:
            return partial(check_isinst, typ=datetime if isinstance(typ, datetime) else date)
        elif verb == IJ:
            base = datetime if issubclass(typ, datetime) or loose_json else date
            return partial(check_value_error, parser=base.fromisoformat)


#: Don't accept time data in a ``date`` type.
iso_dates_strict = partial(iso_dates, loose_json=False)


def enums(*, verb, typ, ctx):
    "Rule to convert between enumerated types and strings."
    if issub_safe(typ, Enum):
        if verb == P2J:
            return convert_enum_str
        elif verb == J2P:
            return partial(convert_str_enum, mapping=dict(typ.__members__))
        elif verb == IP:
            return partial(check_isinst, typ=typ)
        elif verb == IJ:
            return partial(contains, frozenset(typ.__members__.keys()))


def optional(*, verb, typ, ctx):
    """
    Handle an ``Optional[inner]`` by passing ``None`` through.
    """
    if verb not in JPI:
        return
    if has_origin(typ, Union, num_args=2):
        if NoneType not in typ.__args__:
            return
        inner = None
        for arg in typ.__args__:
            if arg is not NoneType:
                inner = arg
        if inner is None:
            raise TypeError(f"Could not find inner type for Optional: {typ}")
    else:
        return
    inner = ctx.lookup_inner(verb=verb, typ=inner)
    if verb in JP:
        return partial(convert_optional, inner=inner)
    elif verb in II:
        return partial(check_optional, inner=inner)


def lists(*, verb, typ, ctx):
    """
    Handle a ``List[type]`` or ``Tuple[type, ...]``.

    Trivia: the ellipsis indicates a homogenous tuple; ``Tuple[A, B, C]`` is a more traditional product type.
    """
    if verb not in JPI:
        return
    if has_origin(typ, list, num_args=1):
        (inner,) = typ.__args__
    elif has_origin(typ, tuple, num_args=2):
        (inner, ell) = typ.__args__
        if ell is not Ellipsis:
            return
    else:
        return
    inner = ctx.lookup_inner(verb=verb, typ=inner)
    con = list if verb in (P2J, IJ) else typ.__origin__
    if verb in JP:
        return partial(convert_collection, inner=inner, con=con)
    elif verb in II:
        return partial(check_collection, inner=inner, con=con)


def sets(*, verb, typ, ctx):
    """
    Handle a ``Set[type]`` or ``FrozenSet[type]``.
    """
    if verb not in JPI:
        return
    if not has_origin(typ, (set, frozenset), num_args=1):
        return
    (inner,) = typ.__args__
    con = list if verb in (P2J, IJ) else typ.__origin__
    inner = ctx.lookup_inner(verb=verb, typ=inner)
    if verb in JP:
        return partial(convert_collection, inner=inner, con=con)
    elif verb in II:
        return partial(check_collection, inner=inner, con=con)


def _stringly(*, verb, typ, ctx):
    """
    Rule to handle types that reliably convert directly to strings.

    This is used internally by dicts.
    """
    if verb not in JPI or not issub_safe(typ, (int, str, date, Enum)):
        return
    for base in str, int:
        if issubclass(typ, base):
            if verb in JP:
                return base
            elif verb in II:
                return partial(check_isinst, typ=base)
    for rule in enums, iso_dates:
        action = rule(verb=verb, typ=typ, ctx=ctx)
        if action is not None:
            return action


def dicts(*, verb, typ, ctx):
    """
    Handle a ``Dict[key, value]`` where key is a string, integer or enum type.
    """
    if verb not in JPI:
        return
    if not has_origin(typ, (dict, OrderedDict), num_args=2):
        return
    (key_type, val_type) = typ.__args__
    key_type = _stringly(verb=verb, typ=key_type, ctx=ctx)
    if key_type is None:
        return
    val_type = ctx.lookup_inner(verb=verb, typ=val_type)
    if verb in JP:
        return partial(convert_mapping, key=key_type, val=val_type, con=typ.__origin__)
    elif verb in II:
        return partial(check_mapping, key=key_type, val=val_type, con=typ.__origin__)
