from importlib import import_module
import logging

try:
    from typing import _eval_type
except ImportError:
    _eval_type = None

logger = logging.getLogger(__name__)
J2P = "json_to_python"
P2J = "python_to_json"
IJ = "inspect_json"
IP = "inspect_python"
II = (IJ, IP)
JP = (J2P, P2J)
JPI = (J2P, P2J, IP, IJ)
NoneType = type(None)
SENTINEL = object()


def identity(value):
    return value


def has_origin(typ, origin, *, num_args=None):
    """
    Determines if a concrete class (a generic class with arguments) matches an origin
    and has a specified number of arguments.

    The typing classes use dunder properties such that ``__origin__`` is the generic
    class and ``__args__`` are the type arguments.
    """
    try:
        t_origin = typ.__origin__
    except AttributeError:
        return False
    else:
        if not isinstance(origin, tuple):
            origin = (origin,)
        return t_origin in origin and (
            num_args is None or len(typ.__args__) == num_args
        )


def issub_safe(sub, sup):
    try:
        return issubclass(sub, sup)
    except TypeError:
        return False


def resolve_fwd_ref(typ, context_class):
    """
    Tries to resolve a forward reference given a containing class. This does nothing for
    regular types.
    """
    resolved = None
    try:
        namespace = vars(import_module(context_class.__module__))
    except AttributeError:
        logger.warning("Couldn't determine module of %r", context_class)
    else:
        resolved = _eval_type(typ, namespace, {})
    if resolved is None:
        return typ
    else:
        return resolved


if _eval_type is None:
    # If typing's internal API changes, we have tests that break.
    def resolve_fwd_ref(typ, context_class):  # noqa
        return typ


_missing_values = set()
try:
    import attr

    _missing_values.add(attr.NOTHING)
except ImportError:
    pass
try:
    import dataclasses

    _missing_values.add(dataclasses.MISSING)
except ImportError:
    pass


def is_attrs_field_required(field):
    """
    Determine if a field's default value is missing.
    """
    if field.default not in _missing_values:
        return False
    try:
        factory = field.default_factory
    except AttributeError:
        return True
    else:
        return factory in _missing_values
