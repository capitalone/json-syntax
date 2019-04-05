'''
Some miscellany to keep the type_strategies module a bit more readable.
'''
from hypothesis import strategies as st

import attr
try:
    import dataclasses as dc
except ImportError:
    dc = None
from datetime import date
from enum import IntEnum
from keyword import iskeyword
import os
import typing


MAX_FIELDS = 8
_max_cp = None if os.environ.get('UNICODE_NAMES') else 0x7f
_any_char = st.characters(min_codepoint=1, max_codepoint=_max_cp)
_ident_start = st.characters(whitelist_categories=['Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl'],
                             max_codepoint=_max_cp)
_ident_tail = st.characters(whitelist_categories=['Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl', 'Mn', 'Mc', 'Nd', 'Pc'],
                            whitelist_characters="_",
                            max_codepoint=_max_cp)


@st.composite
def _idents(draw, lengths=st.integers(min_value=0, max_value=80)):
    chars = [draw(_ident_start)]
    chars.extend(draw(_ident_tail) for _ in range(draw(lengths)))
    chars = ''.join(chars)
    if iskeyword(chars):
        chars += draw(_ident_tail)
    return chars


def _make_enum(name, elems):
    # print(f'IntEnum(enum_{name}, {elems!r})')
    return IntEnum('enum_' + name, elems)


idents = _idents()
enums = st.builds(_make_enum, idents, st.lists(idents, min_size=1, max_size=MAX_FIELDS, unique=True))


def fields_idents(types):
    return st.dictionaries(idents, types, dict_class=list, min_size=0, max_size=MAX_FIELDS)


class _Faux(attr.validators._InstanceOfValidator):
    def __call__(self, inst, attr, value):
        pass


def attrs(types, frozen):
    def _make(name, fields, **kw):
        def _attrib(typ):
            # Add a bogus validator because from_type reads that, not `type`
            # Can't use the real one because of generic types!
            return attr.ib(type=typ, validator=_Faux(typ))
        # print(f'attrs({name}, {fields}, **{kw})')
        return attr.make_class(
            'attrs_' + name, {field: _attrib(typ) for field, typ in fields}, frozen=frozen, **kw
        )

    return st.builds(
        _make,
        idents,
        fields_idents(types),
        slots=st.booleans()
    )


if dc is not None:
    def dataclasses(types, frozen):
        def _make(name, fields, order):
            # print(f'dataclass({name}, {fields}, frozen={frozen}, order={order}')
            return dc.make_dataclass('dc_' + name, fields, frozen=frozen, eq=True, order=order)

        return st.builds(_make, idents, fields_idents(types),
                         order=st.booleans())
else:
    def dataclasses(types, frozen):
        return None


try:
    _NamedTuple = typing.NamedTuple
except AttributeError:
    def namedtuples(types):
        return None
else:
    def namedtuples(types):
        def _make(name, fields):
            # print(f'namedtuple({name}, {fields})')
            return _NamedTuple('nt_' + name, fields)
        return st.builds(_make, idents, fields_idents(types))


def lists(types):
    return st.builds(lambda a: typing.List[a], types)


def hmg_tuples(types):
    return st.builds(lambda a: typing.Tuple[a, ...], types)


def sets(types):
    return st.builds(lambda a: typing.Set[a], types)


def frozensets(types):
    return st.builds(lambda a: typing.FrozenSet[a], types)


_dict_keys = atoms = st.one_of([
    st.sampled_from([int, str, date]),
    enums
])


def dicts(val_types):
    return st.builds(lambda k, v: typing.Dict[k, v], _dict_keys, val_types)


def prod_tuples(types):
    return st.builds(lambda a: typing.Tuple[tuple(a)], st.lists(types, min_size=1, max_size=MAX_FIELDS))


def unions(types, max_size=None):
    return st.builds(lambda a: typing.Union[tuple(a)], st.lists(types, min_size=1, max_size=max_size))
