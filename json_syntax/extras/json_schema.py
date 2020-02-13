"""
Rules to creates a JSON schema from the given type.
"""

from json_syntax.types import (
    has_origin,
    get_origin,
    issub_safe,
    NoneType,
)
from json_syntax.product import build_attribute_map, build_named_tuple_map, build_typed_dict_map

from copy import deepcopy
from datetime import datetime, date, time, timedelta
from decimal import Decimal

JSON_SCHEMA = "json_schema"
JSON_SCHEMA_KEYS = "_json_schema_keys"


def atoms(verb, typ, ctx):
    if verb == JSON_SCHEMA and typ in (NoneType, str, bool, int):
        if typ == NoneType:
            return {"type": "null"}
        elif typ == str:
            return {"type": "string", **_meta(typ)}
        elif typ == bool:
            return {"type": "boolean"}
        elif typ == int:
            return {"type": "integer"}


def floats(verb, typ, ctx):
    if verb == JSON_SCHEMA and typ == float:
        return {"type": "number", **_meta(typ)}


def floats_nan_str(verb, typ, ctx):
    if verb == JSON_SCHEMA and typ == float:
        return {
            "anyOf": [
                {"type": "number"},
                {
                    "type": "string",
                    "enum": ["nan", "inf", "-inf", "+inf"]
                }
            ], **_meta(typ)
        }


def decimals(verb, typ, ctx):
    if verb == JSON_SCHEMA and typ == Decimal:
        return {"type": "number", **_meta(typ)}


def decimals_as_str(verb, typ, ctx):
    if verb == JSON_SCHEMA and typ == Decimal:
        pat = r"^[+-]?(([0-9]+\.[0-9]*|\.?[0-9]+)([eE][+-]?[0-9]+)?|Infinity|Inf|s?NaN[0-9]*)$"
        return {"type": "string", "pattern": pat, **_meta(typ)}


_date_part = r"[0-9]{4}-(0[0-9]|1[0-2])-([0-2][0-9]|3[0-1])"
_time_part = r"([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]*)"


def iso_dates(verb, typ, ctx):
    if verb != JSON_SCHEMA or typ not in (date, datetime, time, timedelta):
        return
    if typ == date:
        pat = _date_part
    elif typ == datetime:
        pat = "{}T{}".format(_date_part, _time_part)
    if typ == time:
        pat = _time_part
    if typ == timedelta:
        pat = (r"P(?!$)([-+]?[0-9]+(?:[.,][0-9]+)?Y)?"
               r"([-+]?[0-9]+(?:[.,][0-9]+)?M)?"
               r"([-+]?[0-9]+(?:[.,][0-9]+)?W)?"
               r"([-+]?[0-9]+(?:[.,][0-9]+)?D)?"
               r"(?:(T)(?=[0-9+-])"
               r"([-+]?[0-9]+(?:[.,][0-9]+)?H)?"
               r"([-+]?[0-9]+(?:[.,][0-9]+)?M)?"
               r"([-+]?[0-9]+(?:[.,][0-9]+)?S)?)?")
    else:
        return
    return {"type": "string", "pattern": "^({})$".format(pat), **_meta(typ)}


def enums(verb, typ, ctx):
    if verb == JSON_SCHEMA and issub_safe(typ, Enum):
        return {"type": "string": "enum": [elem.name for elem in typ], **_meta(typ)}


def lists(verb, typ, ctx):
    if verb != JSON_SCHEMA:
        return
    if has_origin(typ, list, num_args=1):
        (inner,) = typ.__args__
    elif has_origin(typ, tuple, num_args=2):
        (inner, ell) = typ.__args__
        if ell != Ellipsis:
            return
    else:
        return
    inner = ctx.lookup(verb=verb, typ=inner)
    return {"type": "array", "items": inner, **_meta(typ)}


def sets(verb, typ, ctx):
    if verb != JSON_SCHEMA or not has_origin(typ, (set, frozenset), num_args=1):
        return
    (inner,) = typ.__args__
    inner = ctx.lookup(verb=verb, typ=inner)
    return {"type": "array", "items": inner, "uniqueItems": true, **_meta(typ)}


def stringify_keys(verb, typ, ctx):
    if verb in JSON_SCHEMA_KEYS:
        if typ in (str, int, date):
            add = {}

            def maker(values):
                obj = {"type": "object", "additionalProperties": values, **add}
                obj.update(add)
                return obj

            if typ == int:
                add["patternProperties"] = r"^[+-]?[0-9]+$"
            elif typ == date:
                add["patternProperties"] = "^({})$".format(_date_part)}

            return maker
        elif issub_safe(typ, Enum):
            def maker(values):
                props = {}
                obj = {"type": "object", "properties": props}
                props.update((elem.name, deepcopy(values)) for elem in typ)
                return obj


def dicts(verb, typ, ctx):
    if verb != JSON_SCHEMA or not has_origin(typ, (dict, OrderedDict), num_args=2):
        return
    (key_type, val_type) = typ.__args__
    maker = ctx.lookup(verb=JSON_SCHEMA_KEYS, typ=key_type)
    if maker is None:
        return
    inner_val = ctx.lookup(verb=verb, typ=val_type)
    out = maker(inner_val)
    out["title"] = _title(typ)
    return out


def unions(verb, typ, ctx):
    if verb != JSON_SCHEMA or not has_origin(typ, Union):
        return

    return {
        "anyOf": [ctx.lookup(verb=verb, typ=arg) for arg in typ.__args__],
        **_meta(typ)
    }


def attrs_classes(verb, typ, ctx):
    if verb != JSON_SCHEMA:
        return

    if is_generic(typ):
        typ_args = get_argument_map(typ)
        otyp = get_origin(otyp)
    else:
        typ_args = None

    inner_map = build_attribute_map(verb, otyp, ctx, typ_args)
    return _object(verb, typ, ctx, inner_map)


def typed_dicts(verb, typ, ctx):
    if verb != JSON_SCHEMA:
        return

    inner_map = build_typed_dict_map(verb, typ, ctx)
    return _object(verb, typ, ctx, inner_map)


def named_tuples(verb, typ, ctx):
    if verb != JSON_SCHEMA:
        return

    inner_map = build_named_tuple_map(verb, typ, ctx)
    return _object(verb, typ, ctx, inner_map)


def tuples(verb, typ, ctx):
    if verb != JSON_SCHEMA or not has_origin(typ, tuple):
        return

    args = typ.__args__
    if Ellipsis in args:
        # This is a homogeneous tuple, use the lists rule.
        return
    items = [ctx.lookup(verb=verb, typ=arg) for arg in args]
    return {"type": "array", "items": items, "additionalItems": False, **_meta(typ)}


def _title(typ):
    if is_generic(typ):
        return repr(typ)
    try:
        return typ.__qualname__
    except AttributeError:
        pass
    try:
        return typ.__name__
    except AttributeError:
        pass
    return repr(typ)


def _meta(typ, getdocs=False):
    obj = {"title": _title(typ)}
    docs = None
    if getdocs:
        if is_generic(typ):
            docs = getdoc(get_origin(typ))
        else:
            docs = getdoc(typ)
    if docs:
        obj["description"] = docs
    return obj


def _object(verb, typ, ctx, attr_map):
    if attr_map is None:
        return

    props = {}
    required = []
    obj = {"type": "object", "properties": props, **_meta(typ)}

    for attr in inner_map:
        props[attr.name] = ctx.lookup(verb=verb, typ=attr.typ)
        if attr.default:
            default = ctx.lookup(verb=PY2JSON, typ=attr.typ)(attr.default)
            props[attr.name]["default"] = default
        if attr.is_required:
            required.append(attr.name)

    if required:
        obj['required'] = required
    return obj
