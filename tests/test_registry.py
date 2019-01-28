import pytest

from json_syntax import registry
import typing as t


'''
To walk through what the registry needs to do, let's consider the scenarios.

Registering Converters
======================

When we write Converters, we need to register them, and we principally want to register them by type.

*In the simple case*, converters can be looked up entirely by type. In particular, a generic converter, e.g. List[X], can handle any `List` by delegating the contents to a converter that handles X.

*In the complex case*, we've registered additional converters that can handle the same types, and we're going to use some kind of rules to match them. Most likely, a generic rule is that a concrete match wins over a constructed match. And we "construct" a match by searching for the type's "__base__" and then attempting to fill in the arguments.

(I'm also assuming that when we're constructing an encoder that the types are fully specified, but maybe not.)

I think the most comprehensible way to handle special rules is to enable injecting converters into the system. That is, you might have a type like:

    @attr.s(auto_attribs=True)
    class Bob:
       foo: Foo

    @attr.s(auto_attribs=True)
    class Foo:
       a: int
       b: int

Thus the root converter is automatically determined as `root=AttrsConverter(Bob, foo=AttrsConverter(Foo, a=IntConv(), b=IntConv))`.

Say `b` can be a label, you might want `manual = ManualConverter(py_js=label_to_int, js_py=int_to_label)`.

Then `root = root.rewrite('bob.b', manual)`. We can probably be more clever with the rewrite rules or use metadata in
attrs classes to help with the common cases.

Constructed Types
=================

If we request a concrete type from a registry and it doesn't have that specific type, we can try setting matching various permutations of the type, setting various parameters to null.

That's the pattern matching approach.

The types already describe their bases, though, so assuming we write our own `issubclass`, what do we know?

  * List[int] has `list` as its `__base__`.
  * If we have a converter that supports `Sequence[+X]`, it has the `__base__ == collections.Sequence`, and itt `issubclass(list, coll.Sequence)`.
  * `+X` is `TypeVar(X, covariant=True)`

'''


def test_store_types():
    '''
    Types need to be stored and retrieved correctly.
    '''
    subject = registry.Registry()
    subject[bool] = 'bool'
    subject[int] = 'int'
    subject[t.List[int]] = 'List of int'
    subject[t.List[t.TypeVar('X')]] = 'List of X'

    assert subject[bool] == 'bool'
    assert subject[int] == 'int'
    assert subject[t.List] == 'List'
    assert subject[t.List[t.TypeVar('X')] = 'List of X'
    assert subject[t.List[int]] == 'List of int'


class TestRegistry(registry.Registry):
    def compose(self, head, **args):
        _args = ', '.join(f'{name}={value}'
                          for name, value
                          in sorted(args.items()))
        return f'{head}[{_args}]'


def test_constructed_type():
    '''
    A complex type should be broken into parts.
    '''
    subject = TestRegistry()

    subject[str] = 'str'
    subject[int] = 'int'
    subject[t.List[t.TypeVar('X')] = 'List'
    subject[t.Dict[t.TypeVar('K'), t.TypeVar('V')] = 'Dict'

    assert t.List[int] not in subject
    assert subject[t.Dict[str, t.List[int]]] == 'Dict[K=str, V=List[int]]'
    assert subject[t.List[int]] == 'List[X=int]'
