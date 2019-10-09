from hypothesis import given, settings, HealthCheck

from . import type_strategies as ts

# import attr
# from datetime import date, datetime
# from decimal import Decimal
# from enum import Enum
# from itertools import product
# from typing import Union, List, Tuple, Set, FrozenSet, Dict

from json_syntax import std_ruleset
from json_syntax.helpers import PY2JSON, JSON2PY  # INSP_PY, INSP_JSON, NoneType
from json_syntax.pattern import Matches


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100, deadline=None)
@given(ts.type_value_pairs(ts.complex_no_unions))
def test_roundtrip(pair):
    typ, py_value = pair
    rs = std_ruleset()
    act = rs.lookup(verb=PY2JSON, typ=typ)
    json_value = act(py_value)
    act2 = rs.lookup(verb=JSON2PY, typ=typ)
    rt_py_value = act2(json_value)
    assert py_value == rt_py_value


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100, deadline=None)
@given(ts.type_value_pairs(ts.unions_of_simple))
def test_roundtrip_union_simple(pair):
    typ, py_value = pair
    rs = std_ruleset()
    act = rs.lookup(verb=PY2JSON, typ=typ)
    json_value = act(py_value)
    act2 = rs.lookup(verb=JSON2PY, typ=typ)
    rt_py_value = act2(json_value)
    if not rs.is_ambiguous(typ=typ, threshold=Matches.potential):
        assert py_value == rt_py_value


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100, deadline=None)
@given(ts.type_value_pairs(ts.complex_anything))
def test_roundtrip_arbitrary_complex(pair):
    typ, py_value = pair
    rs = std_ruleset()
    act = rs.lookup(verb=PY2JSON, typ=typ)
    json_value = act(py_value)
    act2 = rs.lookup(verb=JSON2PY, typ=typ)
    rt_py_value = act2(json_value)
    if not rs.is_ambiguous(typ=typ, threshold=Matches.potential):
        assert py_value == rt_py_value
