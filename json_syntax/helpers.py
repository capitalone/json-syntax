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
        self.context = str(context)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_value is None or not self.context:
                return

            args = list(exc_value.args)
            arg_num, point = getattr(exc_value, "_context", (None, None))

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
            args[arg_num] = arg[:point] + self.context + arg[point:]
            exc_value.args = tuple(args)
            exc_value._context = (arg_num, point)
        except Exception:
            # Swallow exceptions to avoid adding confusion.
            pass
