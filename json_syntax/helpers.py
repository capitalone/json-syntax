from importlib import import_module
import logging
import typing as t
import sys

_eval_type = getattr(t, "_eval_type", None)
logger = logging.getLogger(__name__)
JSON2PY = "json_to_python"
PY2JSON = "python_to_json"
INSP_JSON = "inspect_json"
INSP_PY = "inspect_python"
PATTERN = "show_pattern"
NoneType = type(None)
SENTINEL = object()
python_minor = sys.version_info[:2]


def identity(value):
    return value


def has_origin(typ, origin, num_args=None):
    """
    Determines if a concrete class (a generic class with arguments) matches an origin
    and has a specified number of arguments.

    The typing classes use dunder properties such that ``__origin__`` is the generic
    class and ``__args__`` are the type arguments.

    Note: in python3.7, the ``__origin__`` attribute changed to reflect native types.
    This call attempts to work around that so that 3.5 and 3.6 "just work."
    """
    t_origin = get_origin(typ)
    if not isinstance(origin, tuple):
        origin = (origin,)
    return t_origin in origin and (num_args is None or len(typ.__args__) == num_args)


def get_origin(typ):
    try:
        t_origin = typ.__origin__
    except AttributeError:
        return None
    else:
        return _origin_pts(t_origin)


try:
    _Generic = t.GenericMeta
except AttributeError:
    _Generic = t._GenericAlias


def is_generic(typ):
    """
    Return true iff the instance (which should be a type value) is a generic type.

    `typing` module notes:

       3.5: typing.List[int] is an instance of typing._GenericAlias
       3.6, 3.7: typing.List[int] is an instance of typing.GenericMeta
    """
    return isinstance(typ, _Generic)


if python_minor < (3, 7):
    import collections as c

    _map = [
        (t.Tuple, tuple),
        (t.List, list),
        (t.Dict, dict),
        (t.Callable, callable),
        (t.Type, type),
        (t.Set, set),
        (t.FrozenSet, frozenset),
    ]
    seen = {prov for prov, stable in _map}
    from collections import abc

    for name, generic in vars(t).items():
        if not is_generic(generic) or generic in seen:
            continue
        for check in getattr(abc, name, None), getattr(c, name.lower(), None):
            if check:
                _map.append((generic, check))
                continue
    _pts = {prov: stable for prov, stable in _map}
    _stp = {stable: prov for prov, stable in _map}

    def _origin_pts(origin, _pts=_pts):
        """
        Convert the __origin__ of a generic type returned by the provisional typing API (python3.5) to the stable version.
        """
        return _pts.get(origin, origin)

    def _origin_stp(origin, _stp=_stp):
        """
        Convert the __origin__ of a generic type in the stable typing API (python3.6+) to the provisional version.
        """
        return _stp.get(origin, origin)

    del _pts
    del _stp
    del _map
    del seen
    del abc
    del c
else:
    _origin_pts = _origin_stp = identity


def issub_safe(sub, sup):
    """
    Safe version of issubclass. Tries to be consistent in handling generic types.

    `typing` module notes:

       3.5, 3.6: issubclass(t.List[int], list) returns true
       3.7: issubclass(t.List[int], list) raises a TypeError
    """
    try:
        return not is_generic(sub) and issubclass(sub, sup)
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


def _add_context(context, exc):
    try:
        args = list(exc.args)
        arg_num, point = getattr(exc, "_context", (None, None))

        if arg_num is None:
            for arg_num, val in enumerate(args):
                if isinstance(val, str):
                    args[arg_num] = args[arg_num] + "; at " if val else "At "
                    break
            else:  # This 'else' clause runs if we don't `break`
                arg_num = len(args)
                args.append("At ")
            point = len(args[arg_num])

        arg = args[arg_num]
        args[arg_num] = arg[:point] + str(context) + arg[point:]
        exc.args = tuple(args)
        exc._context = (arg_num, point)
    except Exception:
        # Swallow exceptions to avoid adding confusion.
        pass


class ErrorContext:
    """
    Inject contextual information into an exception message. This won't work for some exceptions like OSError that
    ignore changes to `args`; likely not an issue for this library. There is a neglible performance hit if there is
    no exception.

    >>> with ErrorContext('.foo'):
    ...   with ErrorContext('[0]'):
    ...     with ErrorContext('.qux'):
    ...       1 / 0
    Traceback (most recent call last)
    ZeroDivisionError: division by zero; at .foo[0].qux

    The `__exit__` method will catch the exception and look for a `_context` attribute assigned to it. If none exists,
    it appends `; at ` and the context string to the first string argument.

    As the exception walks up the stack, outer ErrorContexts will be called. They will see the `_context` attribute and
    insert their context immediately after `; at ` and before the existing context.

    Thus, in the example above:

        ('division by zero',)  -- the original message
        ('division by zero; at .qux',)  -- the innermost context
        ('division by zero; at [0].qux',)
        ('division by zero; at .foo[0].qux',) -- the outermost context

    For simplicity, the method doesn't attempt to inject whitespace. To represent names, consider surrounding
    them with angle brackets, e.g. `<Class>`
    """

    def __init__(self, context):
        self.context = context

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is not None:
            _add_context(self.context, exc_value)


def err_ctx(context, func):
    """
    Execute a callable, decorating exceptions raised with error context.

    ``err_ctx(context, func)`` has the same effect as:

    >>> with ErrorContext(context):
    ...   return func()
    """
    try:
        return func()
    except Exception as exc:
        _add_context(context, exc)
        raise
