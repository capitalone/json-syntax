import pytest

from json_syntax.registry import Registry
import typing as t

parametrize = pytest.mark.parametrize


@parametrize('registry', [
    [],
    [list],
    [t.List[int]],
    [frozenset],
    [t.Dict[str, t.List[bytes]]],
    [t.SupportsInt],
    [list, t.List[int], frozenset, t.Dict[str, t.List[bytes]], t.SupportsInt],
])
@parametrize('atom', [int, bool, str, bytes, type(None), 'int', 'str'])
def test_store_atoms(atom, registry):
    subject = Registry()
    for elem in registry:
        subject[elem] = 'dummy'

    subject[atom] = 'target'
    assert subject[atom] == 'target'


def test_matches_type(registry, instance):
    pass
