from datetime import datetime
import math
from operator import attrgetter


def convert_date_loosely(value):
    return datetime.fromisoformat(value).date()


def check_parse_error(value, *, parser, error):
    try:
        parser(value)
    except error:
        return False
    else:
        return True


def check_isinst(value, *, typ):
    return isinstance(value, typ)


def convert_float(value):
    value = float(value)
    if math.isfinite(value):
        return value
    elif math.isnan(value):
        return "NaN"
    elif value < 0.0:
        return "-Infinity"
    else:
        return "Infinity"


def check_float(value):
    return (
        isinstance(value, (int, float))
        or isinstance(value, str)
        and value.lower()
        in ("nan", "inf", "infinity" "-inf", "-infinity", "+inf", "+infinity")
    )


convert_enum_str = attrgetter("name")


def convert_none(value):
    if value is not None:
        raise ValueError("Expected None")
    return None


def check_str_enum(value, *, mapping):
    return isinstance(value, str) and value in mapping


def convert_str_enum(value, *, mapping):
    return mapping[value]


def convert_optional(value, *, inner):
    if value is None:
        return None
    return inner(value)


def check_optional(value, *, inner):
    return value is None or inner(value)


def convert_collection(value, *, inner, con):
    return con(map(inner, value))


def check_collection(value, *, inner, con):
    return isinstance(value, con) and all(map(inner, value))


def convert_mapping(value, *, key, val, con):
    return con((key(k), val(v)) for k, v in value.items())


def check_mapping(value, *, key, val, con):
    return isinstance(value, con) and all(key(k) and val(v) for k, v in value.items())


def convert_dict_to_attrs(value, *, pre_hook, inner_map, con):
    value = pre_hook(value)
    args = {}
    for name, inner in inner_map:
        try:
            arg = value[name]
        except KeyError:
            pass
        else:
            args[name] = inner(arg)
    return con(**args)


def check_dict(value, *, inner_map, pre_hook):
    value = pre_hook(value)
    if not isinstance(value, dict):
        return False
    for name, inner, required in inner_map:
        try:
            arg = value[name]
        except KeyError:
            if required:
                return False
        else:
            if not inner(arg):
                return False
    return True


def convert_attrs_to_dict(value, *, post_hook, inner_map):
    out = {}
    for name, inner, default in inner_map:
        field = getattr(value, name)
        if field == default:
            continue
        out[name] = inner(field)
    if post_hook is not None:
        out = getattr(value, post_hook)(out)
    return out


def convert_tuple_as_list(value, *, inner, con):
    return con(cvt(val) for val, cvt in zip(value, inner))


def check_tuple_as_list(value, *, inner, con):
    return (
        isinstance(value, con)
        and len(value) == len(inner)
        and all(chk(val) for val, chk in zip(value, inner))
    )


def check_union(value, *, steps):
    return any(step(value) for step in steps)


def convert_union(value, *, steps, typename):
    for check, convert in steps:
        if check(value):
            return convert(value)
    raise ValueError(f"Expected value of type {typename}")
