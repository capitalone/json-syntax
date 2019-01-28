from .helpers import JP, J2P, P2J, NOTHING, resolve_fwd_ref, identity, issub_safe
from .convert import convert_dict_to_attrs, convert_attrs_to_dict

from functools import partial


def attrs_classes(*, verb, typ, ctx, pre_hook='before_json', post_hook='after_json'):
    '''
    Handle an ``@attr.s`` or ``@dataclass`` decorated class.
    '''
    try:
        fields = typ.__attrs_attrs__
    except AttributeError:
        try:
            fields = typ.__dataclass_fields__
        except AttributeError:
            return
        else:
            fields = fields.values()
    if verb == J2P:
        pre_hook_method = getattr(typ, pre_hook, identity)
        inner_map = []
        for field in fields:
            if not field.init:
                continue
            inner = ctx.lookup_inner(verb=verb, typ=resolve_fwd_ref(field.type, typ), accept_missing=True)
            inner_map.append((field.name, inner))
        return partial(convert_dict_to_attrs, pre_hook=pre_hook_method, inner_map=tuple(inner_map), con=typ)
    elif verb == P2J:
        post_hook_method = getattr(typ, post_hook, identity)
        inner_map = []
        for field in fields:
            if not field.init:
                continue
            inner = ctx.lookup_inner(verb=verb, typ=resolve_fwd_ref(field.type, typ), accept_missing=True)
            inner_map.append((field.name, inner, field.default))
        return partial(convert_attrs_to_dict, post_hook=post_hook_method, inner_map=tuple(inner_map))


def named_tuples(*, verb, typ, ctx):
    '''
    Handle a ``NamedTuple(name, [('field', type), ('field', type)])`` type.

    Also handles a ``collections.namedtuple`` if you have a fallback handler.
    '''
    if verb not in JP or not issub_safe(typ, tuple):
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
    if verb == J2P:
        inner_map = []
        for name, inner in fields:
            inner = ctx.lookup_inner(verb=verb, typ=resolve_fwd_ref(inner, typ), accept_missing=True)
            inner_map.append((name, inner))
        return partial(convert_dict_to_attrs, pre_hook=identity, inner_map=tuple(inner_map), con=typ)
    elif verb == P2J:
        defaults = getattr(typ, '_fields_defaults', {})
        inner_map = []
        for name, inner in fields:
            inner = ctx.lookup_inner(verb=verb, typ=resolve_fwd_ref(inner, typ), accept_missing=True)
            inner_map.append((name, inner, defaults.get(name, NOTHING)))
        return partial(convert_attrs_to_dict, post_hook=identity, inner_map=tuple(inner_map))
