from .helpers import (
    JPI,
    J2P,
    P2J,
    IP,
    IJ,
    SENTINEL,
    resolve_fwd_ref,
    identity,
    issub_safe,
    is_attrs_field_required,
    has_origin,
)
from .convert import (
    convert_dict_to_attrs,
    convert_attrs_to_dict,
    check_attrs,
    check_dict,
    convert_tuple_as_list,
    check_tuple_as_list,
)

from functools import partial


def attrs_classes(*, verb, typ, ctx, pre_hook="before_json", post_hook="after_json"):
    """
    Handle an ``@attr.s`` or ``@dataclass`` decorated class.
    """
    if verb not in JPI:
        return
    try:
        fields = typ.__attrs_attrs__
    except AttributeError:
        try:
            fields = typ.__dataclass_fields__
        except AttributeError:
            return
        else:
            fields = fields.values()

    inner_map = []
    for field in fields:
        if field.init:
            tup = (field.name, ctx.lookup_inner(verb=verb, typ=resolve_fwd_ref(field.type, typ), accept_missing=True))
            if verb == P2J:
                tup += (field.default,)
            elif verb == IJ:
                tup += (is_attrs_field_required(field),)
            inner_map.append(tup)

    if verb == J2P:
        pre_hook_method = getattr(typ, pre_hook, identity)
        return partial(convert_dict_to_attrs, pre_hook=pre_hook_method, inner_map=tuple(inner_map), con=typ)
    elif verb == P2J:
        post_hook_method = getattr(typ, post_hook, identity)
        return partial(convert_attrs_to_dict, post_hook=post_hook_method, inner_map=tuple(inner_map))
    elif verb == IP:
        return partial(check_attrs, inner_map=inner_map, con=typ)
    elif verb == IJ:
        return partial(check_dict, inner_map=inner_map)


def named_tuples(*, verb, typ, ctx):
    """
    Handle a ``NamedTuple(name, [('field', type), ('field', type)])`` type.

    Also handles a ``collections.namedtuple`` if you have a fallback handler.
    """
    if verb not in JPI or not issub_safe(typ, tuple):
        return
    try:
        fields = typ._field_types
    except AttributeError:
        try:
            fields = typ._fields
        except AttributeError:
            return
        fields = [(name, None) for name in fields]
    else:
        fields = fields.items()
    defaults = getattr(typ, "_fields_defaults", {})
    inner_map = []
    for name, inner in fields:
        tup = (name, ctx.lookup_inner(verb=verb, typ=resolve_fwd_ref(inner, typ), accept_missing=True))
        if verb == P2J:
            tup += (defaults.get(name, SENTINEL),)
        elif verb == IJ:
            tup += (name not in defaults,)
        inner_map.append(tup)

    if verb == J2P:
        return partial(convert_dict_to_attrs, pre_hook=identity, inner_map=tuple(inner_map), con=typ)
    elif verb == P2J:
        return partial(convert_attrs_to_dict, post_hook=identity, inner_map=tuple(inner_map))
    elif verb == IP:
        return partial(check_attrs, inner_map=inner_map, con=typ)
    elif verb == IJ:
        return partial(check_dict, inner_map=inner_map)


def tuples(*, verb, typ, ctx):
    """
    Handle a ``Tuple[type, type, type]`` product type. Use a ``NamedTuple`` if you don't want a list.
    """
    if verb not in JPI or not has_origin(typ, tuple):
        return
    args = typ.__args__
    if Ellipsis in args:
        # This is a homogeneous tuple, use the lists rule.
        return
    inner = [ctx.lookup_inner(verb=verb, typ=arg) for arg in args]
    if verb == J2P:
        return partial(convert_tuple_as_list, inner=inner, con=tuple)
    elif verb == P2J:
        return partial(convert_tuple_as_list, inner=inner, con=list)
    elif verb == IP:
        return partial(check_tuple_as_list, inner=inner, con=tuple)
    elif verb == IJ:
        return partial(check_tuple_as_list, inner=inner, con=list)
