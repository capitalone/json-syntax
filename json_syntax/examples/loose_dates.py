from json_syntax.helpers import JSON2PY, PY2JSON, INSP_JSON, INSP_PY
from json_syntax.action_v1 import check_parse_error, check_has_type

from datetime import date, datetime
from functools import partial

"""
This example is of working around common date issues.

The standard rules use the standard library's fromisoformat and isoformat methods, to abide by the principle of least surprise.

But it's pretty common to have to consume a datetime in a date field, and it may also be the case that you want to discard the timestamp.

(Note: requires python3.7 or greater.)
"""


def convert_date_loosely(value):
    return datetime.fromisoformat(value).date()


def iso_dates_loose(verb, typ, ctx):
    if typ == date:
        if verb == PY2JSON:
            return date.isoformat
        elif verb == JSON2PY:
            return convert_date_loosely
        elif verb == INSP_PY:
            return partial(check_has_type, typ=date)
        elif verb == INSP_JSON:
            return partial(
                check_parse_error,
                parser=convert_date_loosely,
                error=(TypeError, ValueError),
            )
