from .helpers import has_origin, JP, J2P, P2J, IJ, IP, II
from .action_v1 import convert_union, check_union

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
        if verb in JP:
            if verb == P2J:
                check_verb = IP
            elif verb == J2P:
                check_verb = IJ
            else:
                return
            steps = []
            for arg in typ.__args__:
                check = ctx.lookup(verb=check_verb, typ=arg)
                convert = ctx.lookup(verb=verb, typ=arg)
                steps.append((check, convert))
            return partial(convert_union, steps=steps, typename=repr(typ))
        elif verb in II:
            steps = []
            for arg in typ.__args__:
                check = ctx.lookup(verb=verb, typ=arg)
                steps.append(check)
            return partial(check_union, steps=steps)
