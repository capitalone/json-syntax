"""
A module to help with product types in Python.
"""

from .helpers import issub_safe, resolve_fwd_ref, SENTINEL

_TypedDictMeta = None
try:
    from typing import _TypedDictMeta
except ImportError:
    try:
        from typing_extensions import _TypeDictMeta  # noqa
    except ImportError:
        pass


_attrs_missing_values = set()
try:
    import attr

    _attrs_missing_values.add(attr.NOTHING)
except ImportError:
    pass
try:
    import dataclasses

    _attrs_missing_values.add(dataclasses.MISSING)
except ImportError:
    pass


class Attribute:
    """
    Generic class to describe an attribute for a product type that can be represented as, e.g., a JSON map.

    An Attribute is associated with an action, specifically, its "inner" field directs how to process the inside type,
    not necessarily what the inside type is.

    See the various build_* commands to generate attribute maps. (These are really just lists of Attribute instances.)

    Fields:
      name: the attribute name
      init_name: the constructor name
      inner: the action to take given the verb and the attribute's type
      default: a static default Python value
      is_required: a boolean indicating if the attribute is required
    """

    __slots__ = ("name", "typ", "inner", "default", "is_required")

    def __init__(self, name, typ, is_required, default=SENTINEL, inner=None):
        self.name = name
        self.typ = typ
        self.inner = inner
        self.default = default
        self.is_required = is_required

    @property
    def init_name(self):
        return self.name

    def __repr__(self):
        return "<Attribute {!r}; {}>".format(
            self.name, "required" if self.is_required else "optional"
        )


class AttrsAttribute(Attribute):
    @property
    def init_name(self):
        return self.name.lstrip('_')


def is_attrs_field_required(field):
    """
    Determine if a field can calculate its default value.
    """
    if field.default not in _attrs_missing_values:
        return False
    try:
        factory = field.default_factory
    except AttributeError:
        return True
    else:
        return factory in _attrs_missing_values


def attr_map(verb, outer, ctx, gen):
    result = []
    failed = []
    for att in gen:
        if att.typ is not None:
            try:
                att.typ = resolve_fwd_ref(att.typ, outer)
            except TypeError:
                failed.append("resolve fwd ref {} for {}".format(att.typ, att.name))
        if att.inner is None:
            att.inner = ctx.lookup(
                verb=verb, typ=resolve_fwd_ref(att.typ, outer), accept_missing=True
            )
        if att.inner is None:
            if att.typ is None:
                failed.append("get fallback for {}".format(att.name))
            else:
                failed.append("get {} for {}".format(att.typ, att.name))
        result.append(att)

    if failed:
        raise TypeError(
            "{}({}) failed while trying to: {}".format(verb, outer, ", ".join(failed))
        )
    return tuple(result)


def build_attribute_map(verb, typ, ctx):
    """
    Examine an attrs or dataclass type and construct a list of attributes.

    Returns a list of Attribute instances, or None if the type is not an attrs or dataclass type.
    """
    try:
        fields, con = typ.__attrs_attrs__, AttrsAttribute
    except AttributeError:
        try:
            fields, con = typ.__dataclass_fields__, Attribute
        except AttributeError:
            return
        else:
            fields = fields.values()

    return attr_map(
        verb,
        typ,
        ctx,
        gen=(
            con(
                name=field.name,
                typ=field.type,
                is_required=is_attrs_field_required(field),
                default=field.default
            )
            for field in fields
            if field.init
        ),
    )


def build_named_tuple_map(verb, typ, ctx):
    """
    Examine a named tuple type and construct a list of attributes.

    Returns a list of Attribute instances, or None if the type is not a named tuple.
    """
    if not issub_safe(typ, tuple):
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

    defaults = {}
    try:
        defaults.update(typ._fields_defaults)
    except AttributeError:
        pass
    try:
        defaults.update(typ._field_defaults)
    except AttributeError:
        pass

    return attr_map(
        verb,
        typ,
        ctx,
        (
            Attribute(
                name=name,
                typ=inner,
                is_required=name not in defaults,
                default=defaults.get(name, SENTINEL),
            )
            for name, inner in fields
        ),
    )


def build_typed_dict_map(verb, typ, ctx):
    """
    Examine a TypedDict class and construct a list of attributes.

    Returns a list of Attribute instances, or None if the type is not a typed dict.
    """
    if (
        _TypedDictMeta is None
        or not issub_safe(typ, dict)
        or typ.__class__ is not _TypedDictMeta
    ):
        return

    return attr_map(
        verb,
        typ,
        ctx,
        (
            Attribute(name=name, typ=inner, is_required=True, default=SENTINEL)
            for name, inner in typ.__annotations__.items()
        ),
    )
