"""
This module constructs its own fake type and a rule to support it.

This lets you construct a quick set of enums that are represented as strings.
"""

from ..helpers import JSON2PY, PY2JSON, INSP_JSON, INSP_PY
from functools import partial


class Flag(type):
    """
    An example of a custom type that lets you quickly create string-only flags.

    This also demonstrates a technique that makes it possible to create a fake type that can be
    used within ``typing.Union``.

    Thanks to __class_getitem__, you can invoke this as ``Flag['foo', 'bar', 'etc']``
    but this requires Python 3.7!
    """

    def __new__(cls, *args, **kwds):
        """This is necessary to be a subclass of `type`, which is necessary to be used in a Union."""
        return super().__new__(cls, cls.__name__, (), {})

    def __init__(self, *elems):
        """"""
        if not elems:
            raise TypeError("Flag must be called with at least one string argument.")
        if not all(isinstance(elem, str) for elem in elems):
            raise TypeError("Flag elements must all be strings.")
        self.elems = frozenset(elems)
        if len(self.elems) != len(elems):
            raise TypeError("Duplicate elements are prohibited.")

    def __class_getitem__(cls, elems):
        return cls(*elems) if isinstance(elems, tuple) else cls(elems)

    def __repr__(self):
        return f'{self.__class__.__name__}[{", ".join(map(repr, self.elems))}]'


def _check_flag(elems, value):
    """
    Checks that a value is a member of a set of flags.

    Note that we use a top-level function and `partial`. The trouble with lambdas or local defs is that they
    can't be pickled because they're inaccessible to the unpickler.

    If you don't intend to pickle your encoders, though, they're completely fine to use in rules.
    """
    return isinstance(value, str) and value in elems


def _convert_flag(elems, value):
    """
    Checks the value is in elems and returns it.
    """
    if value not in elems:
        raise ValueError(f'Expect {value!r} to be one of {", ".join(map(repr, elems))}')

    return value


def flags(*, verb, typ, ctx):
    """
    A simple rule to allow certain strings as flag values, but without converting them to an actual Enum.

    This rule is triggered with a fake type ``Flag['string', 'string', 'string']``.
    """
    if not isinstance(typ, Flag):
        return
    if verb in (JSON2PY, PY2JSON):
        return partial(_convert_flag, typ.elems)
    elif verb in (INSP_JSON, INSP_PY):
        return partial(_check_flag, typ.elems)
