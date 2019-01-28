from .helpers import has_origin, issub_safe, NoneType, JP, J2P, P2J
from .convert import (convert_none, convert_date_loosely, convert_enum_str, convert_str_enum, convert_optional,
                      convert_sequence)

from datetime import datetime, date
from enum import Enum
from functools import partial
from typing import Union

'''
These are standard rules to handle various types.

All rules take a verb, a Python type and a context, which is generally a RuleSet. A rule returns a conversion function for that verb.
'''


def atoms(*, verb, typ, ctx):
    "Rule to handle atoms on both sides."
    if verb in JP and issub_safe(typ, (str, float, int, NoneType)):
        if typ is NoneType:
            return convert_none
        for base in (str, float, bool, int):
            if issubclass(typ, base):
                return base


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


#: Don't accept time data in a ``date`` type.
iso_dates_strict = partial(iso_dates, loose_json=False)


def enums(*, verb, typ, ctx):
    "Rule to convert between enumerated types and strings."
    if issub_safe(typ, Enum):
        if verb == P2J:
            return convert_enum_str
        elif verb == J2P:
            return partial(convert_str_enum, mapping=typ.__members__)


def optional(*, verb, typ, ctx):
    '''
    Handle an ``Optional[inner]`` by passing ``None`` through.
    '''
    if verb in JP and has_origin(typ, Union, num_args=2):
        if NoneType not in typ.__args__:
            return
        inner = None
        for arg in typ.__args__:
            if arg is not NoneType:
                inner = arg
        if inner is None:
            raise TypeError(f"Could not find inner type for Optional: {typ}")
        inner = ctx.lookup_inner(verb=verb, typ=inner)
        return partial(convert_optional, inner=inner)


def list_or_tuple(*, verb, typ, ctx):
    '''
    Handle a ``List[type]`` or ``Tuple[type, ...]``. Note: the ellipsis indicates a homogenous tuple.
    '''
    if verb in JP:
        if has_origin(typ, list, num_args=1):
            (inner,) = typ.__args__
        elif has_origin(typ, tuple, num_args=2):
            (inner, ell) = typ.__args__
            if ell is not Ellipsis:
                return
        else:
            return
        inner = ctx.lookup_inner(verb=verb, typ=inner)
        return partial(convert_sequence, inner=inner, con=typ.__origin__)


def set_or_frozenset(*, verb, typ, ctx, json_accepts_sets=False):
    '''
    Handle a ``Set[type]`` or ``FrozenSet[type]``.
    '''
    if verb in JP:
        if has_origin(typ, (set, frozenset), num_args=1):
            (inner,) = typ.__args__
            if verb == J2P or json_accepts_sets:
                con = typ.__origin__
            else:
                con = list
            inner = ctx.lookup_inner(verb=verb, typ=inner)
            return partial(convert_sequence, inner=inner, con=con)
