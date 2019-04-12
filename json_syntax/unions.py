from .helpers import has_origin, JSON2PY, PY2JSON, INSP_JSON, INSP_PY, PATTERN
from .action_v1 import convert_union, check_union
from . import pattern as pat

from functools import partial
from typing import Union


def unions(verb, typ, ctx):
    """
    Handle undiscriminated unions of the form ``Union[A, B, C, D]`` by inspecting the
    inner types one by one.

    This is the "implicit discriminant" technique, exploiting the fact that Python
    already tags all values with their type.

    A potential problem is that the JSON structure may not retain that information. So
    another rule could attempt to add a discriminant to the JSON data. For example, if
    you had two ``attrs`` style classes, they could add a `type` field with the class
    name. As there are many ways to do that, this rule doesn't attempt to pick one for
    you.

    Note: The optional rule handles the common case of ``Union[T, NoneType]`` more
    efficiently, so it should be before this.
    """
    if has_origin(typ, Union):
        if verb in (JSON2PY, PY2JSON):
            if verb == PY2JSON:
                check_verb = INSP_PY
            elif verb == JSON2PY:
                check_verb = INSP_JSON
            else:
                return
            steps = [
                (
                    ctx.lookup(verb=check_verb, typ=arg),
                    ctx.lookup(verb=verb, typ=arg),
                    "<{!s}>".format(arg),
                )
                for arg in typ.__args__
            ]
            return partial(convert_union, steps=steps, typename=repr(typ))
        elif verb in (INSP_JSON, INSP_PY):
            steps = [
                (ctx.lookup(verb=verb, typ=arg), "<{!s}>".format(arg))
                for arg in typ.__args__
            ]
            return partial(check_union, steps=steps)
        elif verb == PATTERN:
            alts = [ctx.lookup(verb=verb, typ=arg) for arg in typ.__args__]
            return pat.Alternatives(alts)
