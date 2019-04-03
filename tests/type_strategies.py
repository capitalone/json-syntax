from hypothesis import strategies as st

from decimal import Decimal
import datetime as dt
from enum import Enum

from . import _strategies as _st


# Tests often want to compare for equality, and there's no good way to do this with NaNs breaking it. :-(
st.register_type_strategy(Decimal, st.decimals(allow_nan=False))
st.register_type_strategy(float, st.floats(allow_nan=False))


def type_value_pairs(base):
    @st.composite
    def tv_pairs(draw):
        typ = draw(base)
        try:
            val = draw(st.from_type(typ))
        except Exception as exc:
            exc.args += (typ,)
            raise
        return (typ, val)

    return tv_pairs()


atoms = st.sampled_from([
    type(None),
    bool,
    int,
    float,
    Decimal,
    str,
    dt.date,
    dt.datetime,
    dt.time,
    dt.timedelta,
])


class Head(Enum):
    def __init__(self, disposition):
        self.disposition = disposition
        self.atomic = disposition == 'atom'
        self.hashable = disposition in ('atom', 'immut')
        self.is_union = disposition == 'union'

    atoms = 'atom'
    enums = 'atom'
    lists = 'mut'
    sets = 'mut'
    dicts = 'mut'
    mut_attrs = 'mut'
    mut_dataclasses = 'mut'
    hmg_tuples = 'immut'
    frozensets = 'immut'
    prod_tuples = 'immut'
    frz_attrs = 'immut'
    frz_dataclasses = 'immut'
    namedtuples = 'immut'
    unions = 'union'

    @classmethod
    def short(cls, elems):
        if isinstance(elems, (cls, str)):
            elems = [elems]
        out = set()
        for elem in elems:
            if isinstance(elem, cls):
                out.add(elem)
            elif isinstance(elem, str):
                out.update(head for head in cls if head.disposition == elem)
        return out


# Need to add:
# 1. default values to all of these
# 2. typeless variants
# 3. our own subclasses?

def map_heads(types, frz_types):
    H = Head
    yield H.atoms, atoms
    yield H.enums, _st.enums
    if types:
        yield H.lists, _st.lists(types)
        yield H.unions, _st.unions(types)
        yield H.mut_attrs, _st.attrs(types, frozen=False)
        yield H.mut_dataclasses, _st.dataclasses(types, frozen=False)
        yield H.dicts, _st.dicts(types)
    if frz_types:
        yield H.hmg_tuples, _st.hmg_tuples(frz_types)
        yield H.sets, _st.sets(frz_types)
        yield H.frozensets, _st.frozensets(frz_types)
        yield H.prod_tuples, _st.prod_tuples(frz_types)
        yield H.frz_attrs, _st.attrs(frz_types, frozen=True)
        yield H.frz_dataclasses, _st.dataclasses(frz_types, frozen=True)
        yield H.namedtuples, _st.namedtuples(frz_types)


def type_tree(*levels):
    '''
    Constructs a type tree of a fixed maximum height based on the heads provided.
    The last level must be leaves that can be contained by the levels above.
    '''
    types, frz_types = None, None

    for level in map(Head.short, reversed(levels)):
        tt = []
        frz_tt = []
        for head, typ in map_heads(types, frz_types):
            if typ is None:
                continue
            if head in level:
                tt.append(typ)
                if head.hashable:
                    frz_tt.append(typ)
        types = st.one_of(tt) if tt else None
        frz_types = st.one_of(frz_tt) if frz_tt else None

    if types is None:
        raise ValueError("No types for {}".format(levels))
    return types


complex_no_unions = type_tree(
    {'atom', 'mut', 'immut'},
    {'atom', 'mut', 'immut'},
    {'atom', 'mut', 'immut'},
    {'atom'}
)

unions_of_simple = type_tree({Head.unions}, {'atom', 'mut', 'immut'}, {'atom'})
