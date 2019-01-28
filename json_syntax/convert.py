from datetime import datetime
from operator import attrgetter


def convert_date_loosely(value):
    return datetime.fromisoformat(value).date()


convert_enum_str = attrgetter('name')


def convert_none(value):
    if value is not None:
        raise TypeError("Expected None")
    return None


def convert_str_enum(value, *, mapping):
    return mapping[value]


def convert_optional(value, *, inner):
    if value is None:
        return None
    return inner(value)


def convert_sequence(value, *, inner, con):
    return con(map(inner, value))


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


def convert_attrs_to_dict(value, *, post_hook, inner_map):
    out = {}
    for name, inner, default in inner_map:
        field = getattr(value, name)
        if field == default:
            continue
        out[name] = inner(field)
    out = post_hook(out)
    return out
