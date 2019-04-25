from .helpers import (
    has_origin,
    get_origin,
    issub_safe,
    NoneType,
    JSON2PY,
    PY2JSON,
    INSP_JSON,
    INSP_PY,
    PATTERN,
)
from .action_v1 import (
    check_collection,
    check_float,
    check_isinst,
    check_has_type,
    check_mapping,
    check_optional,
    check_parse_error,
    check_str_enum,
    convert_collection,
    convert_date,
    convert_datetime,
    convert_decimal_str,
    convert_enum_str,
    convert_float,
    convert_mapping,
    convert_none,
    convert_optional,
    convert_str_enum,
    convert_str_timedelta,
    convert_time,
    convert_timedelta_str,
)
from . import pattern as pat

from collections import OrderedDict
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from enum import Enum
from functools import partial
from typing import Union

"""
These are standard rules to handle various types.

All rules take a verb, a Python type and a context, which is generally a RuleSet. A rule
returns a conversion function for that verb.
"""


def atoms(verb, typ, ctx):
    "Rule to handle atoms on both sides."
    if issub_safe(typ, (str, int, NoneType)):
        if verb in (JSON2PY, PY2JSON):
            if typ is NoneType:
                return convert_none
            for base in (str, bool, int):  # n.b. bool is a subclass of int.
                if typ == base:
                    return base
        elif verb in (INSP_PY, INSP_JSON):
            for base in (NoneType, str, bool, int):
                if typ == base:
                    return partial(check_isinst, typ=base)
        elif verb == PATTERN:
            for base, node in [
                (NoneType, pat.Null),
                (str, pat.String.any),
                (bool, pat.Bool),
                (int, pat.Number),
            ]:
                if typ == base:
                    return node


def floats(verb, typ, ctx):
    """
    Rule to handle floats passing NaNs through unaltered.

    JSON technically recognizes integers and floats. Many JSON generators will represent floats with integral value as
    integers. Thus, this rule will convert both integers and floats in JSON to floats in Python.

    Python's standard JSON libraries treat `nan` and `inf` as special constants, but this is not standard JSON.

    This rule simply treats them as regular float values. If you want to catch them, you can set ``allow_nan=False``
    in ``json.dump()``.
    """
    if typ == float:
        if verb in (JSON2PY, PY2JSON):
            return float
        elif verb == INSP_PY:
            return partial(check_isinst, typ=float)
        elif verb == INSP_JSON:
            return partial(check_isinst, typ=(int, float))
        elif verb == PATTERN:
            return pat.Number


def floats_nan_str(verb, typ, ctx):
    """
    Rule to handle floats passing NaNs through as strings.

    Python's standard JSON libraries treat `nan` and `inf` as special constants, but this is not standard JSON.

    This rule converts special constants to string names.
    """
    if typ == float:
        if verb == JSON2PY:
            return float
        elif verb == PY2JSON:
            return convert_float
        elif verb == INSP_PY:
            return partial(check_isinst, typ=float)
        elif verb == INSP_JSON:
            return check_float
        elif verb == PATTERN:
            return pat.Number


def decimals(verb, typ, ctx):
    """
    Rule to handle decimals natively.

    This rule requires that your JSON library has decimal support, e.g. simplejson.

    Other JSON processors may convert values to and from floating-point; if that's a concern, consider
    `decimals_as_str`.

    This rule will fail if passed a special constant.
    """
    if typ == Decimal:
        if verb in (JSON2PY, PY2JSON):
            return Decimal
        elif verb in (INSP_JSON, INSP_PY):
            return partial(check_isinst, typ=Decimal)
        elif verb == PATTERN:
            return pat.Number


def decimals_as_str(verb, typ, ctx):
    """
    Rule to handle decimals as strings.

    This rule bypasses JSON library decimal support, e.g. simplejson.

    This rule will fail if passed a special constant.
    """
    if typ == Decimal:
        if verb == JSON2PY:
            return Decimal
        elif verb == PY2JSON:
            return convert_decimal_str
        elif verb == INSP_PY:
            return partial(check_isinst, typ=Decimal)
        elif verb in (INSP_JSON, PATTERN):
            inspect = partial(check_parse_error, parser=Decimal, error=ArithmeticError)
            return pat.String("number", inspect) if verb == PATTERN else inspect


def iso_dates(verb, typ, ctx):
    """
    Rule to handle iso formatted datetimes and dates.

    This simply uses the `fromisoformat` and `isoformat` methods of `date` and `datetime`.

    There is a loose variant in the examples that will accept a datetime in a date. A datetime always accepts both
    dates and datetimes.
    """
    if typ not in (date, datetime, time, timedelta):
        return
    if verb == PY2JSON:
        return convert_timedelta_str if typ == timedelta else typ.isoformat
    elif verb == INSP_PY:
        return partial(check_has_type, typ=typ)
    elif verb in (JSON2PY, INSP_JSON, PATTERN):
        if typ == date:
            parse = convert_date
        elif typ == datetime:
            parse = convert_datetime
        elif typ == time:
            parse = convert_time
        elif typ == timedelta:
            parse = convert_str_timedelta
        else:
            return
        if verb == JSON2PY:
            return parse
        inspect = partial(
            check_parse_error, parser=parse, error=(TypeError, ValueError)
        )
        return pat.String(typ.__name__, inspect) if verb == PATTERN else inspect


def enums(verb, typ, ctx):
    "Rule to convert between enumerated types and strings."
    if issub_safe(typ, Enum):
        if verb == PY2JSON:
            return partial(convert_enum_str, typ=typ)
        elif verb == JSON2PY:
            return partial(convert_str_enum, mapping=dict(typ.__members__))
        elif verb == INSP_PY:
            return partial(check_isinst, typ=typ)
        elif verb in (INSP_JSON, PATTERN):
            inspect = partial(check_str_enum, mapping=frozenset(typ.__members__.keys()))
            return pat.String(typ.__name__, inspect) if verb == PATTERN else inspect


def faux_enums(verb, typ, ctx):
    "Rule to fake an Enum by actually using strings."
    if issub_safe(typ, Enum):
        if verb in (JSON2PY, PY2JSON):
            mapping = {name: name for name in typ.__members__}
            return partial(convert_str_enum, mapping=mapping)
        elif verb in (INSP_JSON, INSP_PY, PATTERN):
            inspect = partial(check_str_enum, mapping=frozenset(typ.__members__.keys()))
            return pat.String(typ.__name__, inspect) if verb == PATTERN else inspect


def optional(verb, typ, ctx):
    """
    Handle an ``Optional[inner]`` by passing ``None`` through.
    """
    if verb not in (JSON2PY, PY2JSON, INSP_PY, INSP_JSON, PATTERN):
        return
    if has_origin(typ, Union, num_args=2):
        if NoneType not in typ.__args__:
            return
        inner = None
        for arg in typ.__args__:
            if arg is not NoneType:
                inner = arg
        if inner is None:
            raise TypeError("Could not find inner type for Optional: " + str(typ))
    else:
        return
    inner = ctx.lookup(verb=verb, typ=inner)
    if verb in (JSON2PY, PY2JSON):
        return partial(convert_optional, inner=inner)
    elif verb in (INSP_JSON, INSP_PY):
        return partial(check_optional, inner=inner)
    elif verb == PATTERN:
        return pat.Alternatives([pat.Null, inner])


def lists(verb, typ, ctx):
    """
    Handle a ``List[type]`` or ``Tuple[type, ...]``.

    Trivia: the ellipsis indicates a homogenous tuple; ``Tuple[A, B, C]`` is a product
    type that contains exactly those elements.
    """
    if verb not in (JSON2PY, PY2JSON, INSP_PY, INSP_JSON, PATTERN):
        return
    if has_origin(typ, list, num_args=1):
        (inner,) = typ.__args__
    elif has_origin(typ, tuple, num_args=2):
        (inner, ell) = typ.__args__
        if ell is not Ellipsis:
            return
    else:
        return
    inner = ctx.lookup(verb=verb, typ=inner)
    con = list if verb in (PY2JSON, INSP_JSON, PATTERN) else get_origin(typ)
    if verb in (JSON2PY, PY2JSON):
        return partial(convert_collection, inner=inner, con=con)
    elif verb in (INSP_JSON, INSP_PY):
        return partial(check_collection, inner=inner, con=con)
    elif verb == PATTERN:
        return pat.Array.homog(inner)


def sets(verb, typ, ctx):
    """
    Handle a ``Set[type]`` or ``FrozenSet[type]``.
    """
    if verb not in (JSON2PY, PY2JSON, INSP_PY, INSP_JSON, PATTERN):
        return
    if not has_origin(typ, (set, frozenset), num_args=1):
        return
    (inner,) = typ.__args__
    con = list if verb in (PY2JSON, INSP_JSON, PATTERN) else get_origin(typ)
    inner = ctx.lookup(verb=verb, typ=inner)
    if verb in (JSON2PY, PY2JSON):
        return partial(convert_collection, inner=inner, con=con)
    elif verb in (INSP_JSON, INSP_PY):
        return partial(check_collection, inner=inner, con=con)
    elif verb == PATTERN:
        return pat.Array.homog(inner)


def _stringly(verb, typ, ctx):
    """
    Rule to handle types that reliably convert directly to strings.

    This is used internally by dicts.
    """
    for base in str, int:
        if typ == base:
            if verb == PATTERN and base == str:
                return pat.String.any
            if verb in (JSON2PY, PY2JSON):
                return base
            elif verb == INSP_PY:
                return partial(check_isinst, typ=base)
            elif verb in (INSP_JSON, PATTERN):
                inspect = partial(check_parse_error, parser=base, error=ValueError)
                return pat.String(typ.__name__, inspect) if verb == PATTERN else inspect
    if typ in (datetime, time):
        return
    for rule in enums, iso_dates:
        action = rule(verb=verb, typ=typ, ctx=ctx)
        if action is not None:
            return action


def dicts(verb, typ, ctx):
    """
    Handle a ``Dict[key, value]`` where key is a string, integer, date or enum type.
    """
    if not has_origin(typ, (dict, OrderedDict), num_args=2):
        return
    (key_type, val_type) = typ.__args__
    key_type = _stringly(verb=verb, typ=key_type, ctx=ctx)
    if key_type is None:
        return
    val_type = ctx.lookup(verb=verb, typ=val_type)
    if verb in (JSON2PY, PY2JSON):
        return partial(convert_mapping, key=key_type, val=val_type, con=get_origin(typ))
    elif verb in (INSP_JSON, INSP_PY):
        return partial(check_mapping, key=key_type, val=val_type, con=get_origin(typ))
    elif verb == PATTERN:
        return pat.Object.homog(key_type, val_type)
