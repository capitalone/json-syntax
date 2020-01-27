from .action_v1 import (
    check_parse_error,
    check_str_enum,
    convert_date,
    convert_enum_str,
    convert_str_enum,
)
from .helpers import STR2PY, PY2STR, INSP_STR, issub_safe

from datetime import date
from enum import Enum
from functools import partial


"""
As JSON requires string keys, unless dicts are only allowed to be Dict[str, T], we need to
be able to encode values as strings.

Recommendations:

* The string verbs are not intended for direct use.
* Use these verbs for any type that must be represented as a key in a JSON object.
* The standard rules will only handle types that are reliable keys and have obvious string
  encodings.

See std.dicts for an example.
"""


def stringify_keys(verb, typ, ctx):
    if verb not in (STR2PY, PY2STR, INSP_STR):
        return
    if typ in (str, int):
        if verb == STR2PY:
            return typ
        elif verb == PY2STR:
            return str
        elif verb == INSP_STR:
            return partial(check_parse_error, parser=typ, error=ValueError)
    elif typ == date:
        if verb == PY2STR:
            return typ.isoformat
        elif verb in (STR2PY, INSP_STR):
            parse = convert_date
            if verb == STR2PY:
                return parse
            else:
                return partial(
                    check_parse_error, parser=parse, error=(TypeError, ValueError)
                )
    elif issub_safe(typ, Enum):
        if verb == PY2STR:
            return partial(convert_enum_str, typ=typ)
        elif verb == STR2PY:
            return partial(convert_str_enum, typ=typ)
        elif verb == INSP_STR:
            return partial(check_str_enum, typ=typ)
