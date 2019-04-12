from .helpers import ErrorContext, err_ctx

from datetime import date, datetime, time, timedelta
from decimal import InvalidOperation
import math
import re


def check_parse_error(value, parser, error):
    try:
        parser(value)
    except error:
        return False
    else:
        return True


def check_isinst(value, typ):
    return isinstance(value, typ)


def check_has_type(value, typ):
    return type(value) == typ


def convert_decimal_str(value):
    result = str(value)
    if result == "sNaN":
        raise InvalidOperation("Won't save signalling NaN")
    return result


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


def convert_enum_str(value, typ):
    return typ(value).name


def convert_none(value):
    if value is not None:
        raise ValueError("Expected None")
    return None


def check_str_enum(value, mapping):
    return isinstance(value, str) and value in mapping


def convert_str_enum(value, mapping):
    return mapping[value]


if hasattr(datetime, "fromisoformat"):
    convert_date = date.fromisoformat
    convert_datetime = datetime.fromisoformat
    convert_time = time.fromisoformat
else:
    from dateutil.parser import isoparser

    instance = isoparser(sep="T")
    convert_date = instance.parse_isodate
    convert_datetime = instance.isoparse
    convert_time = instance.parse_isotime
    del instance


def convert_timedelta_str(dur):
    "Barebones support for storing a timedelta as an ISO8601 duration."
    micro = ".{:06d}".format(dur.microseconds) if dur.microseconds else ""
    return "P{:d}DT{:d}{}S".format(dur.days, dur.seconds, micro)


_iso8601_duration = re.compile(
    r"^P(?!$)([-+]?\d+(?:[.,]\d+)?Y)?"
    r"([-+]?\d+(?:[.,]\d+)?M)?"
    r"([-+]?\d+(?:[.,]\d+)?W)?"
    r"([-+]?\d+(?:[.,]\d+)?D)?"
    r"(?:(T)(?=[0-9+-])"
    r"([-+]?\d+(?:[.,]\d+)?H)?"
    r"([-+]?\d+(?:[.,]\d+)?M)?"
    r"([-+]?\d+(?:[.,]\d+)?S)?)?$"
)
_duration_args = {
    "PW": "weeks",
    "PD": "days",
    "TH": "hours",
    "TM": "minutes",
    "TS": "seconds",
}


def convert_str_timedelta(dur):
    if not isinstance(dur, str):
        raise ValueError("Value was not a string.")
    match = _iso8601_duration.match(dur.upper().replace(",", "."))
    section = "P"
    if not match:
        raise ValueError("Value was not an ISO8601 duration.")
    args = {}
    for elem in match.groups():
        if elem is None:
            continue
        if elem == "T":
            section = "T"
            continue
        part = section + elem[-1]
        value = float(elem[:-1])
        if not value:
            continue

        if part in ("PY", "PM"):
            raise ValueError("Year and month durations not supported")
        args[_duration_args[part]] = value
    return timedelta(**args)


def convert_optional(value, inner):
    if value is None:
        return None
    return inner(value)


def check_optional(value, inner):
    return value is None or inner(value)


def convert_collection(value, inner, con):
    return con(
        err_ctx("[{}]".format(i), lambda: inner(val)) for i, val in enumerate(value)
    )


def check_collection(value, inner, con):
    return isinstance(value, con) and all(
        err_ctx("[{}]".format(i), lambda: inner(val)) for i, val in enumerate(value)
    )


def convert_mapping(value, key, val, con):
    return con(err_ctx(k, lambda: (key(k), val(v))) for k, v in value.items())


def check_mapping(value, key, val, con):
    return isinstance(value, con) and all(
        err_ctx(k, lambda: key(k) and val(v)) for k, v in value.items()
    )


def convert_dict_to_attrs(value, pre_hook, inner_map, con):
    value = pre_hook(value)
    args = {}
    for name, inner in inner_map:
        with ErrorContext("[{!r}]".format(name)):
            try:
                arg = value[name]
            except KeyError:
                pass
            else:
                args[name] = inner(arg)
    return con(**args)


def check_dict(value, inner_map, pre_hook):
    value = pre_hook(value)
    if not isinstance(value, dict):
        return False
    for name, inner, required in inner_map:
        with ErrorContext("[{!r}]".format(name)):
            try:
                arg = value[name]
            except KeyError:
                if required:
                    return False
            else:
                if not inner(arg):
                    return False
    return True


def convert_attrs_to_dict(value, post_hook, inner_map):
    out = {}
    for name, inner, default in inner_map:
        with ErrorContext("." + name):
            field = getattr(value, name)
            if field == default:
                continue
            out[name] = inner(field)
    if post_hook is not None:
        out = getattr(value, post_hook)(out)
    return out


def convert_tuple_as_list(value, inner, con):
    return con(
        err_ctx("[{}]".format(i), lambda: cvt(val))
        for i, (val, cvt) in enumerate(zip(value, inner))
    )


def check_tuple_as_list(value, inner, con):
    return (
        isinstance(value, con)
        and len(value) == len(inner)
        and all(
            err_ctx("[{}]".format(i), lambda: chk(val))
            for i, (val, chk) in enumerate(zip(value, inner))
        )
    )


def check_union(value, steps):
    return any(err_ctx(name, lambda: step(value)) for step, name in steps)


def convert_union(value, steps, typename):
    for check, convert, name in steps:
        with ErrorContext(name):
            if check(value):
                return convert(value)
    raise ValueError("Expected value of type {} got {!r}".format(typename, value))
