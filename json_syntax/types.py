from importlib import import_module
import logging
import sys
import typing as t

logger = logging.getLogger(__name__)
_eval_type = getattr(t, "_eval_type", None)
python_minor = sys.version_info[:2]
NoneType = type(None)


def has_origin(typ, origin, num_args=None):
    """
    Determines if a concrete class (a generic class with arguments) matches an origin
    and has a specified number of arguments.

    This does a direct match rather than a subclass check.

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
    """
    Get the constructor origin of a generic type. For example, List is constructed with list.
    """
    try:
        t_origin = typ.__origin__
    except AttributeError:
        return None
    else:
        return _origin_pts(t_origin)


def get_args(typ):
    return getattr(typ, "__args__", None)


def get_generic_origin(typ):
    """
    Get the generic origin of a fully specified type.

    E.g. get_generic_origin(typing.List[int]) == typing.List
    """
    if getattr(typ, "_special", False) is True:
        origin = getattr(t, typ._name)
    else:
        origin = getattr(typ, "__origin__", None)
    return origin if hasattr(origin, "__parameters__") else None


def get_argument_map(typ):
    """
    For a concrete type, e.g. List[int], find the type parameters that map to the arguments.

    This is mostly useful for custom generics, example:

        T = TypeVar('T')
        @attr.s
        class MyGeneric(Generic[T, U]):
            foo = attr.ib(type=T)
            bar = attr.ib(type=List[U])

        get_argument_map(MyGeneric[int, str]) == {T: int, U: str}
    """
    origin = get_generic_origin(typ)
    if origin is None:
        return {}
    return dict(zip(origin.__parameters__, typ.__args__))


def rewrite_typevars(typ, arg_map):
    """
    Rewrites a generic type according to a mapping of arguments.

    Note: behavior is only defined for TypeVar objects.

    From the example under get_argument_map:

       rewrite_typevars(List[U], {T: int, U: str}) == List[str]

    Note that we should immediately apply rewrites.
    """
    if not arg_map:
        # Nothing to rewrite.
        return typ

    try:
        # This is a type variable specified in the arguments.
        return arg_map[typ]
    except (KeyError, TypeError):
        pass

    try:
        args = typ.__args__
    except AttributeError:
        # Not a generic type, we can bail.
        return typ
    else:
        new_args = tuple(rewrite_typevars(arg, arg_map) for arg in args)
        if new_args == args:
            # Don't reconstruct the type when nothing changes.
            return typ
        else:
            # If it passes, construct a new type with the rewritten arguments.
            return get_generic_origin(typ)[new_args]


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
                break
    _pts = {prov: stable for prov, stable in _map}

    def _origin_pts(origin, _pts=_pts):
        """
        Convert the __origin__ of a generic type returned by the provisional typing API (python3.5) to the stable
        version.

        Don't use this, just use get_origin.
        """
        return _pts.get(origin, origin)

    del _pts
    del _map
    del seen
    del abc
    del c
else:

    def _origin_pts(origin):
        return origin


def issub_safe(sub, sup):
    """
    Safe version of issubclass that only compares regular types.

    Tries to be consistent in handling generic types.

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