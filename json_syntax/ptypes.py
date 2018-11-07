'''
Machinery to work with the typing module at runtime.

3. Match generic types.
'''

import typing as t
import collections as c


GENERICS = {
    list: t.List[t.Any],
    tuple: t.Tuple[t.Any, ...],
    dict: t.Dict[t.Any, t.Any],
    callable: t.Callable[..., t.Any],
    set: t.Set[t.Any],
    frozenset: t.FrozenSet[t.Any],
    c.defaultdict: t.DefaultDict[t.Any, t.Any],
    c.deque: t.Deque[t.Any],
    c.ChainMap: t.ChainMap[t.Any, t.Any],
}

def normalize(hint, globals=None, locals=None):
    '''
    Translates a hint into either a `typing` expression or an atomic Python type.
    '''
    if hint is None:
        return type(None)
    if isinstance(value, str):
        value = _ForwardRef(value)
    value = _eval_type(value, globals, locals)
